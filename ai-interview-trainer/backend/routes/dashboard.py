from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from backend.database import get_db
from backend.models import User, Interview
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

    return DashboardStats(
        total_interviews=total,
        completed_interviews=len(completed),
        average_score=avg_score,
        highest_score=highest,
        recent_interviews=[InterviewListItem.model_validate(i) for i in recent],
    )
