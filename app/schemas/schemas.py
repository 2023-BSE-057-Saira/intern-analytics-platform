"""
Pydantic schemas — request/response models for the API
"""
from datetime import date, datetime
from typing import Optional, Any
from pydantic import BaseModel


class InternBase(BaseModel):
    name: str
    email: str
    technology: str
    mentor_id: Optional[int] = None
    batch: Optional[str] = None
    start_date: date
    expected_end_date: Optional[date] = None
    status: str = "active"


class InternCreate(InternBase):
    pass


class InternOut(InternBase):
    intern_id: int

    class Config:
        from_attributes = True


class PredictionOut(BaseModel):
    intern_id: int
    prediction_type: str
    predicted_value: float
    confidence: Optional[float] = None
    explanation: Optional[dict[str, Any]] = None
    created_at: datetime

    class Config:
        from_attributes = True


class RecommendationOut(BaseModel):
    intern_id: int
    recommendation_type: str
    message: str
    created_at: datetime

    class Config:
        from_attributes = True


class PredictionRequest(BaseModel):
    intern_id: int


# --- Auth: registration + password change ---------------------------------
class RegisterRequest(BaseModel):
    name: str
    email: str
    password: str
    technology: str
    batch: Optional[str] = None


class RegisterResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str = "student"
    name: str
    linked_id: int  # the new intern_id


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


# --- Student profile --------------------------------------------------------
class InternProfileOut(BaseModel):
    intern_id: int
    name: str
    email: str
    technology: str
    batch: Optional[str] = None
    status: str
    start_date: date
    expected_end_date: Optional[date] = None
    phone: Optional[str] = None
    education: Optional[str] = None
    skills: Optional[str] = None
    bio: Optional[str] = None
    linkedin_url: Optional[str] = None
    github_url: Optional[str] = None
    avatar_color: Optional[str] = None

    class Config:
        from_attributes = True


class InternProfileUpdate(BaseModel):
    phone: Optional[str] = None
    education: Optional[str] = None
    skills: Optional[str] = None
    bio: Optional[str] = None
    linkedin_url: Optional[str] = None
    github_url: Optional[str] = None


# --- Attendance --------------------------------------------------------------
class AttendanceOut(BaseModel):
    attendance_id: int
    intern_id: int
    date: date
    present: bool

    class Config:
        from_attributes = True


# --- Weekly reports ------------------------------------------------------------
class WeeklyReportCreate(BaseModel):
    week_start_date: date
    hours_worked: Optional[float] = None
    summary: str
    challenges: Optional[str] = None


class WeeklyReportOut(BaseModel):
    report_id: int
    intern_id: int
    week_start_date: date
    hours_worked: Optional[float] = None
    summary: str
    challenges: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# --- Project submissions ---------------------------------------------------------
class ProjectSubmissionCreate(BaseModel):
    title: str
    description: Optional[str] = None
    repo_url: str
    demo_url: Optional[str] = None


class ProjectSubmissionOut(BaseModel):
    submission_id: int
    intern_id: int
    title: str
    description: Optional[str] = None
    repo_url: str
    demo_url: Optional[str] = None
    submitted_at: datetime

    class Config:
        from_attributes = True


class InternUpdate(BaseModel):
    """Admin-only partial update — e.g. assigning a mentor to an
    unassigned self-registered student, or changing status/batch."""
    mentor_id: Optional[int] = None
    batch: Optional[str] = None
    status: Optional[str] = None
    expected_end_date: Optional[date] = None


# --- Tasks --------------------------------------------------------------------
class TaskOut(BaseModel):
    task_id: int
    intern_id: int
    task_name: str
    assigned_date: date
    due_date: Optional[date] = None
    completed_date: Optional[date] = None
    status: str
    difficulty: Optional[str] = None

    class Config:
        from_attributes = True


class TaskStatusUpdate(BaseModel):
    status: str
