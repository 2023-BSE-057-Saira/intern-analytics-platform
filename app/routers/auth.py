"""
app/routers/auth.py
======================
Login endpoint. Frontend posts email+password, gets back a JWT plus
enough info (role, name, linked mentor_id/intern_id) to redirect to
the right dashboard and personalize it immediately.

Also handles public student self-registration and authenticated
password changes.
"""
import random
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.db_models import User, Mentor, Intern
from app.schemas.schemas import RegisterRequest, RegisterResponse, ChangePasswordRequest
from app.security import (
    verify_password, hash_password, create_access_token, get_current_user,
)

router = APIRouter(prefix="/auth", tags=["Auth"])

VALID_TECHNOLOGIES = {"Laravel", "MERN Stack", "Artificial Intelligence", "Flutter", "UI/UX", "DevOps"}
AVATAR_COLORS = ["#2F6FED", "#7C5CFC", "#16A34A", "#D97706", "#DC2626", "#0EA5E9"]


class LoginRequest(BaseModel):
    email: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    name: str
    linked_id: int | None = None  # mentor_id or intern_id, None for admin


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is disabled")

    # Resolve display name + the id the frontend needs for "my dashboard" queries
    name = "Admin"
    linked_id = None
    if user.role == "mentor" and user.mentor_id:
        mentor = db.query(Mentor).filter(Mentor.mentor_id == user.mentor_id).first()
        name = mentor.name if mentor else "Mentor"
        linked_id = user.mentor_id
    elif user.role == "student" and user.intern_id:
        intern = db.query(Intern).filter(Intern.intern_id == user.intern_id).first()
        name = intern.name if intern else "Student"
        linked_id = user.intern_id

    token = create_access_token(data={"sub": str(user.user_id), "role": user.role})
    return LoginResponse(access_token=token, role=user.role, name=name, linked_id=linked_id)


@router.post("/register", response_model=RegisterResponse)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    """
    Public student self-registration. Creates both an Intern record
    (unassigned — no mentor yet, that's an admin action via
    PATCH /interns/{id}) and the matching login (User row), then logs
    them straight in so they land on their dashboard immediately.
    """
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status_code=409, detail="An account with this email already exists")
    if db.query(Intern).filter(Intern.email == payload.email).first():
        raise HTTPException(status_code=409, detail="An intern record with this email already exists")
    if len(payload.password) < 6:
        raise HTTPException(status_code=422, detail="Password must be at least 6 characters")
    if payload.technology not in VALID_TECHNOLOGIES:
        raise HTTPException(
            status_code=422,
            detail=f"technology must be one of: {', '.join(sorted(VALID_TECHNOLOGIES))}",
        )

    intern = Intern(
        name=payload.name,
        email=payload.email,
        technology=payload.technology,
        batch=payload.batch,
        start_date=date.today(),
        status="active",
        avatar_color=random.choice(AVATAR_COLORS),
    )
    db.add(intern)
    db.flush()  # get intern.intern_id without committing yet

    user = User(
        email=payload.email,
        password_hash=hash_password(payload.password),
        role="student",
        intern_id=intern.intern_id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(data={"sub": str(user.user_id), "role": "student"})
    return RegisterResponse(access_token=token, name=intern.name, linked_id=intern.intern_id)


@router.post("/change-password")
def change_password(payload: ChangePasswordRequest, db: Session = Depends(get_db),
                     current_user: User = Depends(get_current_user)):
    if not verify_password(payload.current_password, current_user.password_hash):
        raise HTTPException(status_code=401, detail="Current password is incorrect")
    if len(payload.new_password) < 6:
        raise HTTPException(status_code=422, detail="New password must be at least 6 characters")
    current_user.password_hash = hash_password(payload.new_password)
    db.commit()
    return {"detail": "Password updated successfully"}
