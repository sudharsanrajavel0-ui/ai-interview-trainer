from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from backend.database import get_db
from backend.models import User, Interview, Question, Answer, LoginEvent
from backend.schemas import DashboardStats, InterviewListItem
from backend.utils.security import get_current_user

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])


@router.get("/stats", response_model=DashboardStats)
def get_dashboard_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    interviews = (
        db.query(Interview)
        .filter(Interview.user_id == current_user.id)
        .all()
    )

    total = len(interviews)
    completed = [i for i in interviews if i.status == "completed"]

    avg_score = 0.0
    highest = 0.0
    if completed:
        scores = [i.total_score for i in completed]
        avg_score = round(sum(scores) / len(scores), 1)
        highest = round(max(scores), 1)

    recent = (
        db.query(Interview)
        .filter(Interview.user_id == current_user.id)
        .order_by(Interview.created_at.desc())
        .limit(10)
        .all()
    )

    # CHANGED: User dashboard charts — count of answers scoped to the authenticated user
    questions_answered = (
        db.query(func.count(Answer.id))
        .join(Question, Answer.question_id == Question.id)
        .join(Interview, Question.interview_id == Interview.id)
        .filter(Interview.user_id == current_user.id)
        .scalar()
    ) or 0

    return DashboardStats(
        total_interviews=total,
        completed_interviews=len(completed),
        average_score=avg_score,
        highest_score=highest,
        questions_answered=questions_answered,
        recent_interviews=[InterviewListItem.model_validate(i) for i in recent],
    )
@router.get("/login_history")
def get_login_history(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    events = (
        db.query(LoginEvent)
        .filter(LoginEvent.user_id == current_user.id)
        .order_by(LoginEvent.created_at.desc())
        .limit(50)
        .all()
    )
    return [
        {
            "id": e.id,
            "user_id": e.user_id,
            "email": e.email,
            "success": bool(e.success) if e.success is not None else True,
            "created_at": e.created_at.isoformat() if e.created_at else None,
        }
        for e in events
    ]
