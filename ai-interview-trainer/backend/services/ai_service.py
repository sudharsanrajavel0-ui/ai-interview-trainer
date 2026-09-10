import logging
from typing import Dict, Any

from backend.services.gemini_service import (
    generate_question as _gemini_generate_question,
    evaluate_answer as _gemini_evaluate_answer,
    generate_overall_feedback as _gemini_generate_overall_feedback,
)

logger = logging.getLogger("ai_interview")


def generate_question(
    job_role: str,
    interview_type: str,
    difficulty: str,
    question_number: int,
    previous_questions: list[str] = None,
    question_type: str = "writing",
) -> Dict[str, Any]:
    return _gemini_generate_question(
        job_role=job_role,
        interview_type=interview_type,
        difficulty=difficulty,
        question_number=question_number,
        previous_questions=previous_questions,
        question_type=question_type,
    )


def evaluate_answer(
    question: str,
    answer: str,
    job_role: str,
    interview_type: str,
    difficulty: str,
) -> Dict[str, Any]:
    return _gemini_evaluate_answer(
        question=question,
        answer=answer,
        job_role=job_role,
        interview_type=interview_type,
        difficulty=difficulty,
    )


def generate_overall_feedback(
    job_role: str,
    difficulty: str,
    scores: list[float],
    questions_and_answers: list[dict],
) -> str:
    return _gemini_generate_overall_feedback(
        job_role=job_role,
        difficulty=difficulty,
        scores=scores,
        questions_and_answers=questions_and_answers,
    )
