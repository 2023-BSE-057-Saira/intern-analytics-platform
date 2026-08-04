"""
app/routers/auth.py
======================
Login endpoint. Frontend posts email+password, gets back a JWT plus
enough info (role, name, linked mentor_id/intern_id) to redirect to
the right dashboard and personalize it immediately.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.db_models import User, Mentor, Intern
from app.security import verify_password, create_access_token

router = APIRouter(prefix="/auth", tags=["Auth"])


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
