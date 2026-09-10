import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.orm import joinedload
from datetime import datetime, timezone
import json
from backend.database import get_db
from backend.models import User, Interview, Question, Answer, Feedback
from backend.schemas import (
    InterviewCreate, InterviewResponse, InterviewDetail,
    QuestionResponse, AnswerSubmit, AnswerResponse,
    FeedbackResponse,
)
from backend.utils.security import get_current_user
from backend.services.ai_service import (
    generate_question,
    evaluate_answer,
    generate_overall_feedback,
)

logger = logging.getLogger("ai_interview")

router = APIRouter(prefix="/api/interviews", tags=["Interviews"])


@router.post("", response_model=InterviewResponse, status_code=status.HTTP_201_CREATED)
def create_interview(
    data: InterviewCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    interview = Interview(
        user_id=current_user.id,
        job_role=data.job_role,
        interview_type=data.interview_type,
        difficulty=data.difficulty,
        total_questions=data.total_questions,
        current_question=0,
        total_score=0.0,
        status="in_progress",
    )
    db.add(interview)
    db.commit()
    db.refresh(interview)
    return interview


@router.post("/{interview_id}/questions", response_model=QuestionResponse)
def get_next_question(
    interview_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    logger.info(f"Question request received: interview_id={interview_id}, user_id={current_user.id}")

    interview = db.query(Interview).filter(
        Interview.id == interview_id,
        Interview.user_id == current_user.id,
    ).first()

    if not interview:
        logger.warning(f"Interview {interview_id} not found for user {current_user.id}")
        raise HTTPException(status_code=404, detail="Interview not found")

    if interview.status != "in_progress":
        logger.warning(f"Interview {interview_id} is not in progress (status={interview.status})")
        raise HTTPException(status_code=400, detail="Interview is not in progress")

    if interview.current_question >= interview.total_questions:
        logger.warning(f"Interview {interview_id} has no more questions remaining")
        raise HTTPException(status_code=400, detail="No more questions remaining")

    previous_questions = [
        q.question_text for q in interview.questions
    ]

    question_type = _determine_question_type(interview.difficulty, interview.current_question + 1)

    logger.info(
        f"Generating question {interview.current_question + 1}/{interview.total_questions} "
        f"for role='{interview.job_role}', type='{interview.interview_type}', "
        f"difficulty='{interview.difficulty}', question_type='{question_type}'"
    )

    try:
        generated = generate_question(
            job_role=interview.job_role,
            interview_type=interview.interview_type,
            difficulty=interview.difficulty,
            question_number=interview.current_question + 1,
            previous_questions=previous_questions,
            question_type=question_type,
        )
        question_text = generated.get("question", "")
        logger.info(f"Question generated successfully: '{question_text[:80]}...'")
    except ValueError as e:
        logger.error(f"Question generation value error: {e}")
        raise HTTPException(status_code=503, detail=str(e))
    except RuntimeError as e:
        logger.error(f"Question generation failed: {e}")
        raise HTTPException(status_code=503, detail=str(e))

    question = Question(
        interview_id=interview.id,
        question_number=interview.current_question + 1,
        question_text=question_text,
        question_type=generated.get("question_type", "writing"),
        options=json.dumps(generated.get("options")) if generated.get("options") else None,
        correct_answer=generated.get("correct_answer"),
    )
    db.add(question)

    interview.current_question += 1
    db.commit()
    db.refresh(question)

    logger.info(f"Question {question.question_number} saved for interview {interview_id}")

    payload = {
        "id": question.id,
        "question_number": question.question_number,
        "question_text": question.question_text,
        "question_type": question.question_type,
        "options": json.loads(question.options) if question.options else None,
    }
    return payload


def _determine_question_type(difficulty: str, question_number: int) -> str:
    if difficulty == "beginner":
        return "mcq"
    if difficulty == "advanced":
        return "writing"
    if question_number % 2 == 1:
        return "mcq"
    return "writing"


def _option_letter(option: str) -> str:
    text = (option or "").strip()
    if "." in text:
        letter = text.split(".", 1)[0].strip().upper()
        if len(letter) == 1:
            return letter
    return text.upper()


@router.post("/{interview_id}/answers", response_model=AnswerResponse)
def submit_answer(
    interview_id: int,
    data: AnswerSubmit,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    interview = db.query(Interview).filter(
        Interview.id == interview_id,
        Interview.user_id == current_user.id,
    ).first()

    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found")

    if interview.status != "in_progress":
        raise HTTPException(status_code=400, detail="Interview is not in progress")

    latest_question = (
        db.query(Question)
        .filter(Question.interview_id == interview_id)
        .order_by(Question.question_number.desc())
        .first()
    )

    if not latest_question:
        raise HTTPException(status_code=400, detail="No question to answer")

    existing_answer = db.query(Answer).filter(
        Answer.question_id == latest_question.id
    ).first()
    if existing_answer:
        raise HTTPException(status_code=400, detail="Already answered this question")

    is_mcq = latest_question.question_type == "mcq"

    if is_mcq:
        options = json.loads(latest_question.options) if latest_question.options else []
        options_by_letter = {_option_letter(o): o for o in options}
        selected_raw = (data.selected_option or "").strip()
        selected_letter = _option_letter(selected_raw)

        if selected_letter not in options_by_letter:
            raise HTTPException(status_code=400, detail="Please select an answer.")

        correct = (latest_question.correct_answer or "").strip().upper()
        is_correct = selected_letter == correct
        score = 10.0 if is_correct else 0.0

        model_answer = options_by_letter.get(correct, "")
        candidate_answer = options_by_letter.get(selected_letter, selected_raw)

        if is_correct:
            evaluation = {
                "score": score,
                "strengths": ["Correct answer"],
                "weaknesses": [],
                "suggestions": ["Keep building on this foundation."],
                "model_answer": model_answer,
            }
        else:
            evaluation = {
                "score": score,
                "strengths": [],
                "weaknesses": ["Incorrect option selected"],
                "suggestions": [f"The correct answer is: {model_answer or correct}"],
                "model_answer": model_answer,
            }
    else:
        if not data.answer_text or not data.answer_text.strip():
            raise HTTPException(status_code=400, detail="Please type your answer before submitting")
        try:
            evaluation = evaluate_answer(
                question=latest_question.question_text,
                answer=data.answer_text,
                job_role=interview.job_role,
                interview_type=interview.interview_type,
                difficulty=interview.difficulty,
            )
        except ValueError as e:
            raise HTTPException(status_code=503, detail=str(e))
        except RuntimeError as e:
            logger.error(f"AI answer evaluation failed: {e}")
            raise HTTPException(status_code=503, detail=str(e))
        candidate_answer = data.answer_text

    def _to_json(value):
        if isinstance(value, list):
            return json.dumps(value)
        if isinstance(value, str):
            try:
                parsed = json.loads(value)
                if isinstance(parsed, list):
                    return value
            except (json.JSONDecodeError, TypeError):
                pass
            return json.dumps([value])
        return json.dumps([])

    answer = Answer(
        question_id=latest_question.id,
        candidate_answer=candidate_answer,
        score=evaluation["score"],
    )
    db.add(answer)
    db.flush()

    feedback = Feedback(
        answer_id=answer.id,
        strengths=_to_json(evaluation.get("strengths", [])),
        weaknesses=_to_json(evaluation.get("weaknesses", [])),
        suggestions=_to_json(evaluation.get("suggestions", [])),
        model_answer=evaluation.get("model_answer", ""),
    )
    db.add(feedback)

    interview.total_score += evaluation["score"]
    db.commit()

    db.refresh(answer)
    db.refresh(feedback)

    answer.feedback = feedback
    return answer


@router.post("/{interview_id}/complete", response_model=InterviewDetail)
def complete_interview(
    interview_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    interview = db.query(Interview).filter(
        Interview.id == interview_id,
        Interview.user_id == current_user.id,
    ).first()

    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found")

    if interview.status == "completed":
        raise HTTPException(status_code=400, detail="Interview already completed")

    answered_count = (
        db.query(Answer)
        .join(Question)
        .filter(Question.interview_id == interview_id)
        .count()
    )

    if answered_count == 0:
        raise HTTPException(status_code=400, detail="No answers submitted yet")

    scores = []
    questions_and_answers = []
    for q in interview.questions:
        if q.answer:
            scores.append(q.answer.score)
            questions_and_answers.append({
                "question": q.question_text,
                "answer": q.answer.candidate_answer,
                "score": q.answer.score,
            })

    try:
        overall = generate_overall_feedback(
            job_role=interview.job_role,
            difficulty=interview.difficulty,
            scores=scores,
            questions_and_answers=questions_and_answers,
        )
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except RuntimeError as e:
        logger.error(f"AI overall feedback failed: {e}")
        raise HTTPException(status_code=503, detail=str(e))

    interview.status = "completed"
    interview.completed_at = datetime.now(timezone.utc)
    interview.overall_feedback = overall
    if scores:
        interview.total_score = round(sum(scores) / len(scores), 1)

    db.commit()
    db.refresh(interview)
    return interview


@router.get("/{interview_id}", response_model=InterviewDetail)
def get_interview(
    interview_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    interview = (
        db.query(Interview)
        .options(
            joinedload(Interview.questions)
            .joinedload(Question.answer)
            .joinedload(Answer.feedback)
        )
        .filter(
            Interview.id == interview_id,
            Interview.user_id == current_user.id,
        )
        .first()
    )

    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found")

    return interview


@router.get("", response_model=list[InterviewResponse])
def list_interviews(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    interviews = (
        db.query(Interview)
        .filter(Interview.user_id == current_user.id)
        .order_by(Interview.created_at.desc())
        .all()
    )
    return interviews
