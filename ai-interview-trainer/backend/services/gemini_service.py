import json
import re
import time
import logging
from typing import Dict, Any

import httpx

from backend.config import get_settings
from backend.services.fallback_questions import get_fallback_question

logger = logging.getLogger("ai_interview")
settings = get_settings()

GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
MAX_RETRIES = 3
RETRY_BASE_DELAY = 2.0


def _parse_retry_after(response) -> float:
    header = response.headers.get("Retry-After")
    if not header:
        return 0.0
    try:
        return float(header)
    except (ValueError, TypeError):
        return 0.0


def _backoff_delay(attempt: int, retry_after: float = 0.0) -> float:
    if retry_after and retry_after > 0:
        return min(retry_after, 60.0)
    return min(RETRY_BASE_DELAY * (2 ** attempt), 30.0)


def _get_gemini_key() -> str:
    key = settings.effective_gemini_key
    if not key or key == "YOUR_NEW_GEMINI_API_KEY":
        raise ValueError(
            "Gemini API key is not configured. "
            "Set GEMINI_API_KEY in your .env file. "
            "Get a key at https://aistudio.google.com/apikey"
        )
    return key


def _call_gemini(prompt: str, temperature: float = 0.7,
                 max_output_tokens: int = 500, response_json: bool = False) -> str:
    api_key = _get_gemini_key()
    model = settings.effective_gemini_model
    url = GEMINI_API_URL.format(model=model)

    payload: dict[str, Any] = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": temperature,
            "maxOutputTokens": max_output_tokens,
        },
    }

    if response_json:
        prompt_text = prompt + "\n\nIMPORTANT: Return ONLY valid JSON. No markdown, no code fences, no extra text."
        payload["contents"][0]["parts"][0]["text"] = prompt_text

    last_error = None
    for attempt in range(MAX_RETRIES):
        if attempt > 0:
            delay = _backoff_delay(attempt - 1, last_retry_after)
            logger.info(f"Gemini retry {attempt}/{MAX_RETRIES} after {delay:.1f}s delay")
            time.sleep(delay)

        last_retry_after = 0.0
        try:
            logger.info(f"Gemini request attempt {attempt + 1}/{MAX_RETRIES} (model={model})")
            response = httpx.post(
                url,
                params={"key": api_key},
                json=payload,
                headers={
                    "Content-Type": "application/json",
                },
                timeout=60.0,
            )

            if response.status_code == 400:
                body = response.json()
                error_msg = body.get("error", {}).get("message", "Bad request")
                logger.error(f"Gemini 400 error: {error_msg}")
                raise ValueError(f"Gemini API error: {error_msg}")

            if response.status_code == 403:
                logger.error("Gemini API key is invalid or access denied")
                raise ValueError(
                    "Invalid Gemini API key. "
                    "Please check your GEMINI_API_KEY configuration."
                )

            if response.status_code == 429:
                last_retry_after = _parse_retry_after(response)
                logger.warning(
                    f"Gemini rate limit hit on attempt {attempt + 1}/{MAX_RETRIES} "
                    f"(Retry-After: {last_retry_after}s)"
                )
                last_error = RuntimeError(
                    "AI service rate limit exceeded. Please try again later."
                )
                continue

            if response.status_code != 200:
                logger.error(f"Gemini HTTP {response.status_code}: {response.text[:200]}")
                raise RuntimeError(
                    f"Gemini service error (HTTP {response.status_code}). Please try again."
                )

            data = response.json()

            candidates = data.get("candidates", [])
            if not candidates:
                logger.error(f"Gemini returned no candidates: {data}")
                raise RuntimeError("AI returned an empty response. Please try again.")

            parts = candidates[0].get("content", {}).get("parts", [])
            if not parts:
                logger.error(f"Gemini returned no parts: {data}")
                raise RuntimeError("AI returned an empty response. Please try again.")

            text = parts[0].get("text", "").strip()
            if not text:
                raise RuntimeError("AI returned an empty response. Please try again.")

            logger.info(f"Gemini response received successfully on attempt {attempt + 1}")
            return text

        except httpx.TimeoutException:
            logger.error(f"Gemini request timed out on attempt {attempt + 1}")
            last_error = RuntimeError("AI service timed out. Please try again.")
            continue
        except httpx.ConnectError:
            logger.error(f"Could not connect to Gemini API on attempt {attempt + 1}")
            last_error = RuntimeError(
                "Unable to connect to AI service. Please check your internet connection."
            )
            continue
        except (ValueError, RuntimeError) as e:
            raise
        except Exception as e:
            logger.error(f"Unexpected Gemini error on attempt {attempt + 1}: {e}")
            last_error = RuntimeError("An unexpected error occurred while contacting the AI service.")
            continue

    logger.error(f"Gemini failed after {MAX_RETRIES} attempts")
    if last_error:
        raise last_error
    raise RuntimeError("AI service is currently unavailable. Please try again later.")


def parse_gemini_json(response_text: str) -> Any:
    """Robustly extract a JSON object from a Gemini response.

    Handles pure JSON, JSON wrapped in markdown code fences, JSON embedded in
    surrounding explanation text, empty responses and slightly malformed JSON.
    Returns None if JSON could not be extracted/parsed.
    """
    if not response_text:
        return None

    content = response_text.strip()

    fences = re.findall(r"```(?:json)?\s*([\s\S]*?)```", content)
    candidates = [f.strip() for f in fences if f.strip()]
    candidates.append(content)

    for candidate in candidates:
        block = candidate.strip()
        if block.startswith("{"):
            candidate = block

        try:
            return json.loads(candidate)
        except (json.JSONDecodeError, ValueError):
            pass

        match = re.search(r"\{[\s\S]*\}", candidate)
        if match:
            try:
                return json.loads(match.group())
            except (json.JSONDecodeError, ValueError):
                pass

    return None


def _extract_mcq_from_text(response_text: str) -> Dict[str, Any]:
    """Extract MCQ fields from raw Gemini text without relying on valid JSON.

    Gemini sometimes wraps option text in quotes / escapes them (`B. git commit
    -m \\"Message\\"`) which breaks naive json.loads. This scans for the question,
    the four A.-D. options and the correct answer directly from the text.
    """
    text = response_text or ""

    question = None
    q_match = re.search(r'["\']?question["\']?\s*[:=]\s*["\']([^"\']+)', text)
    if q_match:
        question = q_match.group(1).strip()
    if not question:
        q_match = re.search(r'"question"\s*:\s*"([\s\S]*?)",\s*"options"', text)
        if q_match:
            question = q_match.group(1).strip()
    if not question:
        q_match = re.search(r'"question"\s*:\s*"([\s\S]*?)"\s*,\s*"options"', text)
        if q_match:
            question = q_match.group(1).strip()

    option_pattern = re.compile(r'\b([A-D])\.\s*([^\r\n]+)', re.IGNORECASE)
    matches = {}
    first_option_pos = None
    for line in text.splitlines():
        m = option_pattern.search(line)
        if m:
            letter = m.group(1).upper()
            if letter not in matches:
                value = m.group(2).strip().strip('",').strip()
                matches[letter] = value
            if first_option_pos is None:
                first_option_pos = text.find(line)

    options = []
    for letter in "ABCD":
        option = matches.get(letter)
        if option:
            options.append(f"{letter}. {option}")

    correct = None
    c_letter = re.search(r'"?correct_answer"?\s*[:=]\s*"?([A-D])"?', text, re.IGNORECASE)
    if c_letter:
        correct = c_letter.group(1).upper()
    if not correct:
        c_letter = re.search(r'correct\s+answer\s*:?\s*\(?([A-D])\)?', text, re.IGNORECASE)
        if c_letter:
            correct = c_letter.group(1).upper()

    if not question and len(options) == 4 and first_option_pos is not None:
        prefix = text[:first_option_pos].strip()
        prefix = re.sub(r'^(question|options)\s*[:=]\s*', '', prefix, flags=re.IGNORECASE).strip()
        prefix_lines = [ln for ln in prefix.splitlines() if not re.match(r'\b[A-D]\.', ln.strip(), re.IGNORECASE)]
        if prefix_lines:
            question = " ".join(ln.strip() for ln in prefix_lines if ln.strip()).strip().strip('",').strip()
        if not question and prefix:
            question = prefix.strip().strip('",').strip()

    if not question or len(options) != 4 or not correct:
        return None

    return {
        "correct_answer": correct,
        "options": options,
        "question": question,
    }


def _mcq_response_raw(prompt: str) -> str:
    return _call_gemini(prompt, temperature=0.7, max_output_tokens=1024, response_json=True)


def _normalize_mcq(result: Dict[str, Any]) -> Dict[str, Any]:
    """Validate and normalize a parsed Gemini MCQ response into the canonical shape.

    Returns a dict with question, question_type ('mcq'), options (exactly 4
    non-empty strings), correct_answer (the option letter A-D) and explanation,
    or raises ValueError if the data is invalid.
    """
    if not isinstance(result, dict):
        raise ValueError("MCQ response is not a JSON object")

    question = result.get("question")
    if not isinstance(question, str) or not question.strip():
        raise ValueError("MCQ missing question")

    if result.get("question_type") not in ("mcq", "MCQ", "multiple_choice"):
        raise ValueError(f"Invalid question_type: {result.get('question_type')!r}")

    options = result.get("options")
    if not isinstance(options, list):
        raise ValueError("MCQ missing options")

    options = [str(o).strip() for o in options if isinstance(o, str) and o.strip()]
    if len(options) != 4:
        raise ValueError(f"MCQ must have exactly 4 options, got {len(options)}")

    clean_options = []
    for letter, opt in zip("ABCD", options):
        text = re.sub(rf"^\s*{re.escape(letter)}\s*[.:)]\s*", "", opt).strip()
        clean_options.append(text)

    correct = str(result.get("correct_answer", "")).strip()
    if not correct:
        raise ValueError("MCQ missing correct answer")

    correct_letter = None
    if correct.upper() in ("A", "B", "C", "D"):
        correct_letter = correct.upper()
    else:
        for letter, opt_text in zip("ABCD", clean_options):
            if correct.lower() == opt_text.lower() or correct.lower() == f"{letter}. {opt_text}".lower():
                correct_letter = letter
                break

    if correct_letter is None:
        raise ValueError("MCQ correct answer does not match any option")

    explanation = result.get("explanation")
    if not isinstance(explanation, str):
        explanation = ""

    letter_options = [f"{letter}. {text}" for letter, text in zip("ABCD", clean_options)]

    return {
        "question_type": "mcq",
        "question": question.strip(),
        "options": letter_options,
        "correct_answer": correct_letter,
        "explanation": explanation,
    }


def _generate_mcq(job_role: str, interview_type: str, difficulty: str,
                  question_number: int, previous_questions: list[str]) -> Dict[str, Any]:
    base = (
        "You are an expert AI interviewer creating a multiple-choice interview "
        "question (MCQ).\n"
        f"Candidate role: {job_role}\n"
        f"Interview type: {interview_type}\n"
        f"Difficulty: {difficulty}\n"
        f"Question number: {question_number}\n"
    )

    if previous_questions:
        base += (
            "Previously asked questions (do NOT repeat these):\n"
            + "\n".join(f"- {q}" for q in previous_questions)
            + "\n"
        )

    mcq_rules = (
        "\nCreate exactly ONE multiple-choice question relevant to the role and "
        "difficulty with exactly 4 short, distinct options and exactly ONE correct "
        "answer.\n"
        "Keep the question concise (under 40 words) so the entire JSON fits comfortably "
        "in one response.\n"
        "The options must be distinct and mutually exclusive. Do NOT make the correct "
        "answer obvious (for example by making it much longer or much shorter than the "
        "others). No option except the correct one may be reasonably correct.\n"
    )

    first_prompt = (
        base + mcq_rules +
        "Return ONLY a single valid JSON object. No markdown, no code fences, no "
        "introductory or trailing text, no explanations outside the JSON. Do not "
        "repeat or echo any part of this instruction back to me.\n"
        'Use exactly this structure (the "correct_answer" must exactly match one of '
        'the option strings in "options"):\n'
        '{"question": "<the complete question text>", "question_type": "mcq", '
        '"options": ["<option 1>", "<option 2>", "<option 3>", "<option 4>"], '
        '"correct_answer": "<exact option text of the correct answer>", '
        '"explanation": "<short explanation>"}'
    )

    strict_prompt = (
        base + mcq_rules +
        "Output one machine-readable JSON object ONLY, on a single line, with no "
        "markdown, no code fences, and no words before or after the JSON.\n"
        '{"question":"...","question_type":"mcq","options":["o1","o2","o3","o4"],'
        '"correct_answer":"<exact one of o1-o4>","explanation":"..."}'
    )

    for attempt, prompt in enumerate([first_prompt, strict_prompt], start=1):
        try:
            raw = _mcq_response_raw(prompt)
        except RuntimeError as e:
            logger.warning(f"MCQ Gemini call failed on attempt {attempt}: {e}")
            if attempt >= 2:
                break
            continue
        except ValueError as e:
            logger.warning(f"MCQ Gemini config error on attempt {attempt}: {e}")
            if attempt >= 2:
                break
            continue
        result = parse_gemini_json(raw)
        if not isinstance(result, dict) or not result.get("options"):
            result = _extract_mcq_from_text(raw)
        try:
            return _normalize_mcq(result)
        except ValueError:
            logger.warning(
                f"MCQ validation failed on attempt {attempt}: {raw[:200]}"
            )
            if attempt >= 2:
                break

    logger.info("MCQ generation fell back to the local question bank.")
    return get_fallback_question(
        question_type="mcq",
        difficulty=difficulty,
        role=job_role,
        index=question_number - 1,
    )


def generate_question(
    job_role: str,
    interview_type: str,
    difficulty: str,
    question_number: int,
    previous_questions: list[str] = None,
    question_type: str = "writing",
) -> Dict[str, Any]:
    prompt = (
        "You are an expert AI interviewer conducting a job interview.\n\n"
        f"Candidate role: {job_role}\n"
        f"Interview type: {interview_type}\n"
        f"Difficulty: {difficulty}\n"
        f"Question number: {question_number}\n"
    )

    if previous_questions:
        prompt += (
            "\nPreviously asked questions (do NOT repeat these):\n"
            + "\n".join(f"- {q}" for q in previous_questions)
            + "\n"
        )

    if question_type == "mcq":
        return _generate_mcq(
            job_role=job_role,
            interview_type=interview_type,
            difficulty=difficulty,
            question_number=question_number,
            previous_questions=previous_questions,
        )

    prompt += (
        "\nQuestion type: WRITTEN ANSWER\n"
        "Generate exactly ONE challenging interview question that requires a written, "
        "paragraph-style answer. Do NOT generate a multiple-choice question.\n"
        "The question must be relevant to the candidate's role and difficulty level.\n"
        "- Do NOT provide the answer or any explanation.\n"
        "- Do NOT ask multiple questions.\n"
        "- Return ONLY the question text. No preamble, no numbering."
    )

    try:
        question_text = _call_gemini(prompt, temperature=0.7, max_output_tokens=200).strip()
    except RuntimeError as e:
        logger.warning(f"Writing question Gemini call failed: {e}")
        logging.warning("Falling back to local question bank for writing question.")
        fallback = get_fallback_question(
            question_type="writing",
            difficulty=difficulty,
            role=job_role,
            index=question_number - 1,
        )
        return {
            "question_type": "writing",
            "question": fallback["question"],
            "options": None,
            "correct_answer": None,
        }

    if not question_text:
        fallback = get_fallback_question(
            question_type="writing",
            difficulty=difficulty,
            role=job_role,
            index=question_number - 1,
        )
        return {
            "question_type": "writing",
            "question": fallback["question"],
            "options": None,
            "correct_answer": None,
        }

    return {
        "question_type": "writing",
        "question": question_text,
        "options": None,
        "correct_answer": None,
    }


def evaluate_answer(
    question: str,
    answer: str,
    job_role: str,
    interview_type: str,
    difficulty: str,
) -> Dict[str, Any]:
    prompt = (
        "You are an expert interview evaluator.\n\n"
        f"Candidate role: {job_role}\n"
        f"Interview type: {interview_type}\n"
        f"Difficulty: {difficulty}\n\n"
        f"Question:\n{question}\n\n"
        f"Candidate's answer:\n{answer}\n\n"
        "Evaluate the answer based on:\n"
        "1. Technical correctness\n"
        "2. Relevance to the question\n"
        "3. Completeness of the response\n"
        "4. Clarity and communication\n"
        "5. Overall quality\n\n"
        "Scoring guide:\n"
        "1-3: Poor — major gaps in understanding\n"
        "4-5: Below average — partial understanding, significant gaps\n"
        "6-7: Good — solid understanding with minor gaps\n"
        "8-9: Very good — comprehensive and accurate\n"
        "10: Excellent — outstanding, demonstrates deep expertise\n\n"
        "Return ONLY a valid JSON object with these exact fields:\n"
        "{\n"
        '  "score": <number between 1 and 10>,\n'
        '  "strengths": [<list of strings>],\n'
        '  "weaknesses": [<list of strings>],\n'
        '  "suggestions": [<list of improvement suggestions>],\n'
        '  "model_answer": "<a concise model answer for the question>"\n'
        "}"
    )

    raw = _call_gemini(prompt, temperature=0.3, max_output_tokens=2048, response_json=True)

    result = parse_gemini_json(raw)

    if not isinstance(result, dict):
        result = None

    if not result:
        match = re.search(r"\{[\s\S]*\"score\"[\s\S]*\}", raw)
        if match:
            try:
                result = json.loads(match.group())
            except (json.JSONDecodeError, ValueError):
                result = None

    if not isinstance(result, dict):
        raise RuntimeError(f"AI returned invalid JSON. Response: {raw[:200]}")

    required_keys = {"score", "strengths", "weaknesses", "suggestions", "model_answer"}
    if not required_keys.issubset(result.keys()):
        missing = required_keys - result.keys()
        raise RuntimeError(f"AI returned incomplete evaluation. Missing: {missing}")

    result["score"] = max(1.0, min(10.0, float(result["score"])))

    for key in ("strengths", "weaknesses", "suggestions"):
        if isinstance(result[key], str):
            result[key] = [result[key]]
        elif not isinstance(result[key], list):
            result[key] = [str(result[key])]

    return result


def generate_overall_feedback(
    job_role: str,
    difficulty: str,
    scores: list[float],
    questions_and_answers: list[dict],
) -> str:
    avg_score = sum(scores) / len(scores) if scores else 0

    qa_text = ""
    for qa in questions_and_answers:
        qa_text += f"Q: {qa['question']}\nScore: {qa['score']}/10\n\n"

    prompt = (
        "You are an expert interview coach.\n\n"
        f"Role: {job_role}\n"
        f"Difficulty: {difficulty}\n"
        f"Average score: {avg_score:.1f}/10\n\n"
        f"Question-by-question results:\n{qa_text}\n"
        "Provide a concise but helpful overall feedback paragraph (3-5 sentences).\n"
        "Be encouraging but honest about areas for improvement.\n"
        "Return ONLY the feedback text. No JSON, no formatting, no preamble."
    )

    return _call_gemini(prompt, temperature=0.5, max_output_tokens=300)
