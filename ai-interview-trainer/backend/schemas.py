import json
from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional, List
from datetime import datetime


class UserCreate(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=100)
    email: str = Field(..., min_length=5, max_length=150)
    password: str = Field(..., min_length=6, max_length=100)


class UserLogin(BaseModel):
    email: str
    password: str


class UserResponse(BaseModel):
    id: int
    full_name: str
    email: str
    created_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str


class InterviewCreate(BaseModel):
    job_role: str = Field(..., min_length=1, max_length=100)
    interview_type: str = Field(..., pattern="^(technical|hr_behavioral|mixed)$")
    difficulty: str = Field(..., pattern="^(beginner|intermediate|advanced)$")
    total_questions: int = Field(..., ge=5, le=20)


class QuestionResponse(BaseModel):
    id: int
    question_number: int
    question_text: str
    question_type: str = "writing"
    options: Optional[List[str]] = None

    class Config:
        from_attributes = True


class AnswerSubmit(BaseModel):
    answer_text: Optional[str] = Field(default=None, max_length=5000)
    selected_option: Optional[str] = Field(default=None, max_length=500)


class FeedbackResponse(BaseModel):
    strengths: List[str] = []
    weaknesses: List[str] = []
    suggestions: List[str] = []
    model_answer: str = ""

    class Config:
        from_attributes = True

    @field_validator("strengths", "weaknesses", "suggestions", mode="before")
    @classmethod
    def parse_list_field(cls, v):
        if isinstance(v, str):
            try:
                parsed = json.loads(v)
                if isinstance(parsed, list):
                    return parsed
            except (json.JSONDecodeError, TypeError):
                return [item.strip() for item in v.split("\n") if item.strip()]
        if isinstance(v, list):
            return v
        return []


class AnswerResponse(BaseModel):
    id: int
    question_id: int
    candidate_answer: str
    score: float
    feedback: Optional[FeedbackResponse] = None

    class Config:
        from_attributes = True


class QuestionWithAnswer(BaseModel):
    id: int
    question_number: int
    question_text: str
    answer: Optional[AnswerResponse] = None

    class Config:
        from_attributes = True


class InterviewResponse(BaseModel):
    id: int
    job_role: str
    interview_type: str
    difficulty: str
    total_questions: int
    current_question: int
    total_score: float
    status: str
    overall_feedback: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class InterviewDetail(InterviewResponse):
    questions: List[QuestionWithAnswer] = []


class InterviewListItem(BaseModel):
    id: int
    job_role: str
    interview_type: str
    difficulty: str
    total_questions: int
    total_score: float
    status: str
    created_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class DashboardStats(BaseModel):
    total_interviews: int
    completed_interviews: int
    average_score: float
    highest_score: float
    recent_interviews: List[InterviewListItem]


class ErrorResponse(BaseModel):
    detail: str
