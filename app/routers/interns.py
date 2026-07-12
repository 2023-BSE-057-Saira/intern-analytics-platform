"""
Endpoints for managing intern records.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.db_models import Intern
from app.schemas.schemas import InternCreate, InternOut

router = APIRouter(prefix="/interns", tags=["Interns"])


@router.post("/", response_model=InternOut)
def create_intern(intern: InternCreate, db: Session = Depends(get_db)):
    db_intern = Intern(**intern.model_dump())
    db.add(db_intern)
    db.commit()
    db.refresh(db_intern)
    return db_intern


@router.get("/", response_model=list[InternOut])
def list_interns(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return db.query(Intern).offset(skip).limit(limit).all()


@router.get("/{intern_id}", response_model=InternOut)
def get_intern(intern_id: int, db: Session = Depends(get_db)):
    intern = db.query(Intern).filter(Intern.intern_id == intern_id).first()
    if not intern:
        raise HTTPException(status_code=404, detail="Intern not found")
    return intern
