import hmac
import json
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.config import get_settings
from backend.database import get_db
from backend.models import User, Interview, Question, Answer, Feedback, LoginEvent, SystemErrorEvent

settings = get_settings()

router = APIRouter(prefix="/api/admin", tags=["Admin"])

ADMIN_COOKIE = "admin_session"
ADMIN_SESSION_TTL = timedelta(hours=8)

_sessions = {}


class AdminLogin(BaseModel):
    username: str
    password: str


def _verify_admin(username: str, password: str) -> bool:
    expected_user = settings.ADMIN_USERNAME or ""
    expected_pass = settings.ADMIN_PASSWORD or ""
    user_ok = hmac.compare_digest(username or "", expected_user)
    pass_ok = hmac.compare_digest(password or "", expected_pass)
    return user_ok and pass_ok


def _new_session_token() -> str:
    token = secrets.token_urlsafe(32)
    _sessions[token] = datetime.now(timezone.utc) + ADMIN_SESSION_TTL
    return token


def get_current_admin(request: Request) -> str:
    token = request.cookies.get(ADMIN_COOKIE)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Admin authentication required",
        )
    expiry = _sessions.get(token)
    if not expiry:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Admin authentication required",
        )
    if expiry < datetime.now(timezone.utc):
        _sessions.pop(token, None)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Admin authentication required",
        )
    return token


def is_admin_authenticated(request: Request) -> bool:
    try:
        get_current_admin(request)
        return True
    except HTTPException:
        return False


def _as_list(value):
    if not value:
        return []
    if isinstance(value, list):
        return [str(x) for x in value]
    try:
        parsed = json.loads(value)
        if isinstance(parsed, list):
            return [str(x) for x in parsed]
        return [str(value)]
    except (json.JSONDecodeError, TypeError):
        return [line.strip() for line in str(value).split("\n") if line.strip()]


def _iso(value):
    return value.isoformat() if value else None


@router.post("/login")
def admin_login(data: AdminLogin, response: Response):
    if not _verify_admin(data.username, data.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin credentials",
        )
    token = _new_session_token()
    response.set_cookie(
        key=ADMIN_COOKIE,
        value=token,
        httponly=True,
        samesite="lax",
        max_age=int(ADMIN_SESSION_TTL.total_seconds()),
        path="/",
    )
    return {"detail": "Admin login successful"}


@router.post("/logout")
def admin_logout(response: Response, token: str = Depends(get_current_admin)):
    _sessions.pop(token, None)
    response.delete_cookie(ADMIN_COOKIE, path="/")
    return {"detail": "Logged out"}


@router.get("/stats")
def admin_stats(db: Session = Depends(get_db), _: str = Depends(get_current_admin)):
    total_users = db.query(func.count(User.id)).scalar() or 0
    total_interviews = db.query(func.count(Interview.id)).scalar() or 0
    total_questions = db.query(func.count(Question.id)).scalar() or 0
    total_answers = db.query(func.count(Answer.id)).scalar() or 0
    completed = (
        db.query(func.count(Interview.id))
        .filter(Interview.status == "completed")
        .scalar()
        or 0
    )
    avg_row = (
        db.query(func.avg(Interview.total_score))
        .filter(Interview.status == "completed")
        .scalar()
    )
    average_score = round(avg_row, 1) if avg_row is not None else 0.0
    return {
        "total_users": total_users,
        "total_interviews": total_interviews,
        "total_questions": total_questions,
        "total_answers": total_answers,
        "total_completed_interviews": completed,
        "average_score": average_score,
    }


@router.get("/users")
def admin_users(db: Session = Depends(get_db), _: str = Depends(get_current_admin)):
    users = db.query(User).order_by(User.id).all()
    return [
        {
            "id": u.id,
            "full_name": u.full_name,
            "email": u.email,
            "created_at": _iso(u.created_at),
            "interview_count": len(u.interviews),
            "completed_interviews": sum(
                1 for i in u.interviews if i.status == "completed"
            ),
        }
        for u in users
    ]


@router.get("/interviews")
def admin_interviews(db: Session = Depends(get_db), _: str = Depends(get_current_admin)):
    rows = (
        db.query(Interview, User)
        .join(User, Interview.user_id == User.id)
        .order_by(Interview.created_at.desc())
        .all()
    )
    return [
        {
            "id": i.id,
            "user_id": i.user_id,
            "user_email": u.email,
            "user_name": u.full_name,
            "job_role": i.job_role,
            "interview_type": i.interview_type,
            "difficulty": i.difficulty,
            "total_questions": i.total_questions,
            "total_score": i.total_score,
            "status": i.status,
            "created_at": _iso(i.created_at),
            "completed_at": _iso(i.completed_at),
        }
        for i, u in rows
    ]


@router.get("/questions")
def admin_questions(db: Session = Depends(get_db), _: str = Depends(get_current_admin)):
    rows = (
        db.query(Question, Interview, User)
        .join(Interview, Question.interview_id == Interview.id)
        .join(User, Interview.user_id == User.id)
        .order_by(Question.id.asc())
        .all()
    )
    return [
        {
            "id": q.id,
            "interview_id": q.interview_id,
            "question_number": q.question_number,
            "question_text": q.question_text,
            "question_type": q.question_type,
            "job_role": iv.job_role,
            "difficulty": iv.difficulty,
            "user_email": u.email,
            "created_at": _iso(q.created_at),
        }
        for q, iv, u in rows
    ]


@router.get("/answers")
def admin_answers(db: Session = Depends(get_db), _: str = Depends(get_current_admin)):
    rows = (
        db.query(Answer, Question, Interview, User, Feedback)
        .join(Question, Answer.question_id == Question.id)
        .join(Interview, Question.interview_id == Interview.id)
        .join(User, Interview.user_id == User.id)
        .outerjoin(Feedback, Feedback.answer_id == Answer.id)
        .order_by(Answer.id.asc())
        .all()
    )
    return [
        {
            "id": a.id,
            "question_id": a.question_id,
            "question_text": q.question_text,
            "candidate_answer": a.candidate_answer,
            "score": a.score,
            "user_email": u.email,
            "user_name": u.full_name,
            "created_at": _iso(a.created_at),
            "strengths": _as_list(f.strengths) if f else [],
            "weaknesses": _as_list(f.weaknesses) if f else [],
            "suggestions": _as_list(f.suggestions) if f else [],
            "model_answer": f.model_answer if f else "",
        }
        for a, q, iv, u, f in rows
    ]


@router.get("/results")
def admin_results(db: Session = Depends(get_db), _: str = Depends(get_current_admin)):
    rows = (
        db.query(Feedback, Answer, Question, Interview, User)
        .join(Answer, Feedback.answer_id == Answer.id)
        .join(Question, Answer.question_id == Question.id)
        .join(Interview, Question.interview_id == Interview.id)
        .join(User, Interview.user_id == User.id)
        .order_by(Feedback.id.asc())
        .all()
    )
    return [
        {
            "id": f.id,
            "answer_id": f.answer_id,
            "user_email": u.email,
            "user_name": u.full_name,
            "interview_id": iv.id,
            "question_id": q.id,
            "question_text": q.question_text,
            "candidate_answer": a.candidate_answer,
            "score": a.score,
            "strengths": _as_list(f.strengths),
            "weaknesses": _as_list(f.weaknesses),
            "suggestions": _as_list(f.suggestions),
            "model_answer": f.model_answer,
            "status": iv.status,
            "completed_at": _iso(iv.completed_at),
        }
        for f, a, q, iv, u in rows
    ]


@router.get("/login_events")
def admin_login_events(db: Session = Depends(get_db), _: str = Depends(get_current_admin)):
    events = db.query(LoginEvent).order_by(LoginEvent.created_at.asc()).all()
    return [
        {
            "id": e.id,
            "user_id": e.user_id,
            "email": e.email,
            "ip_address": e.ip_address,
            "success": bool(e.success) if e.success is not None else True,
            "created_at": _iso(e.created_at),
        }
        for e in events
    ]


@router.get("/error_events")
def admin_error_events(db: Session = Depends(get_db), _: str = Depends(get_current_admin)):
    events = db.query(SystemErrorEvent).order_by(SystemErrorEvent.created_at.asc()).all()
    return [
        {
            "id": e.id,
            "path": e.path,
            "method": e.method,
            "status_code": e.status_code,
            "error_type": e.error_type,
            "created_at": _iso(e.created_at),
        }
        for e in events
    ]