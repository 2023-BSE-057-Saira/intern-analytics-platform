"""
SQLAlchemy ORM models — mirrors sql/schema.sql
"""
from sqlalchemy import (
    Column, Integer, String, Date, Boolean, Numeric, Text, ForeignKey, TIMESTAMP
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class Mentor(Base):
    __tablename__ = "mentors"

    mentor_id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    technology = Column(String(50))
    email = Column(String(100), unique=True)
    max_capacity = Column(Integer, default=8)

    interns = relationship("Intern", back_populates="mentor")


class Intern(Base):
    __tablename__ = "interns"

    intern_id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(100), unique=True)
    technology = Column(String(50), nullable=False)
    mentor_id = Column(Integer, ForeignKey("mentors.mentor_id"))
    batch = Column(String(50))
    start_date = Column(Date, nullable=False)
    expected_end_date = Column(Date)
    status = Column(String(20), default="active")

    mentor = relationship("Mentor", back_populates="interns")


class Attendance(Base):
    __tablename__ = "attendance"

    attendance_id = Column(Integer, primary_key=True, index=True)
    intern_id = Column(Integer, ForeignKey("interns.intern_id"))
    date = Column(Date, nullable=False)
    present = Column(Boolean, nullable=False)


class Task(Base):
    __tablename__ = "tasks"

    task_id = Column(Integer, primary_key=True, index=True)
    intern_id = Column(Integer, ForeignKey("interns.intern_id"))
    task_name = Column(String(200))
    assigned_date = Column(Date, nullable=False)
    due_date = Column(Date)
    completed_date = Column(Date)
    status = Column(String(20), default="pending")
    difficulty = Column(String(20))


class GithubActivity(Base):
    __tablename__ = "github_activity"

    activity_id = Column(Integer, primary_key=True, index=True)
    intern_id = Column(Integer, ForeignKey("interns.intern_id"))
    date = Column(Date, nullable=False)
    commits = Column(Integer, default=0)
    pull_requests = Column(Integer, default=0)
    issues_opened = Column(Integer, default=0)
    issues_closed = Column(Integer, default=0)


class CodeReview(Base):
    __tablename__ = "code_reviews"

    review_id = Column(Integer, primary_key=True, index=True)
    intern_id = Column(Integer, ForeignKey("interns.intern_id"))
    task_id = Column(Integer, ForeignKey("tasks.task_id"))
    reviewer_id = Column(Integer, ForeignKey("mentors.mentor_id"))
    score = Column(Numeric(4, 2))
    feedback = Column(Text)
    review_date = Column(Date, nullable=False)


class MentorFeedback(Base):
    __tablename__ = "mentor_feedback"

    feedback_id = Column(Integer, primary_key=True, index=True)
    intern_id = Column(Integer, ForeignKey("interns.intern_id"))
    mentor_id = Column(Integer, ForeignKey("mentors.mentor_id"))
    rating = Column(Numeric(3, 2))
    feedback_text = Column(Text)
    date = Column(Date, nullable=False)


class CommunicationActivity(Base):
    __tablename__ = "communication_activity"

    comm_id = Column(Integer, primary_key=True, index=True)
    intern_id = Column(Integer, ForeignKey("interns.intern_id"))
    date = Column(Date, nullable=False)
    messages_sent = Column(Integer, default=0)
    meetings_attended = Column(Integer, default=0)


class Prediction(Base):
    __tablename__ = "predictions"

    prediction_id = Column(Integer, primary_key=True, index=True)
    intern_id = Column(Integer, ForeignKey("interns.intern_id"))
    prediction_type = Column(String(50), nullable=False)
    predicted_value = Column(Numeric(6, 4), nullable=False)
    confidence = Column(Numeric(6, 4))
    explanation_json = Column(JSONB)
    created_at = Column(TIMESTAMP, server_default=func.now())


class Recommendation(Base):
    __tablename__ = "recommendations"

    recommendation_id = Column(Integer, primary_key=True, index=True)
    intern_id = Column(Integer, ForeignKey("interns.intern_id"))
    recommendation_type = Column(String(50))
    message = Column(Text)
    created_at = Column(TIMESTAMP, server_default=func.now())

# Add this class to app/models/db_models.py (anywhere after Mentor/Intern
# are defined, since it references both).

class User(Base):
    __tablename__ = "users"

    user_id = Column(Integer, primary_key=True, index=True)
    email = Column(String(100), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False)  # 'admin', 'mentor', 'student'
    mentor_id = Column(Integer, ForeignKey("mentors.mentor_id"), nullable=True)
    intern_id = Column(Integer, ForeignKey("interns.intern_id"), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(TIMESTAMP, server_default=func.now())
