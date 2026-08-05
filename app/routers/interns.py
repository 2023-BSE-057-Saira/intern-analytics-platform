"""
Endpoints for managing intern records.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.db_models import Intern
from app.schemas.schemas import InternCreate, InternOut, InternUpdate
from app.security import require_role

router = APIRouter(prefix="/interns", tags=["Interns"])


@router.post("/", response_model=InternOut)
def create_intern(intern: InternCreate, db: Session = Depends(get_db),
                   current_user=Depends(require_role("admin"))):
    db_intern = Intern(**intern.model_dump())
    db.add(db_intern)
    db.commit()
    db.refresh(db_intern)
    return db_intern


@router.get("/", response_model=list[InternOut])
def list_interns(skip: int = 0, limit: int = 100, db: Session = Depends(get_db),
                  current_user=Depends(require_role("admin", "mentor"))):
    return db.query(Intern).offset(skip).limit(limit).all()


@router.get("/unassigned/list", response_model=list[InternOut])
def list_unassigned_interns(db: Session = Depends(get_db),
                             current_user=Depends(require_role("admin"))):
    """Self-registered students waiting for a mentor to be assigned.
    NOTE: this route must stay ABOVE /{intern_id} below — FastAPI
    matches routes top-to-bottom, and /{intern_id} would otherwise
    swallow this request (treating 'unassigned' as an intern_id and
    failing int validation) before ever reaching this one."""
    return db.query(Intern).filter(Intern.mentor_id.is_(None)).all()


@router.get("/{intern_id}", response_model=InternOut)
def get_intern(intern_id: int, db: Session = Depends(get_db),
                current_user=Depends(require_role("admin", "mentor", "student"))):
    intern = db.query(Intern).filter(Intern.intern_id == intern_id).first()
    if not intern:
        raise HTTPException(status_code=404, detail="Intern not found")
    return intern


@router.patch("/{intern_id}", response_model=InternOut)
def update_intern(intern_id: int, payload: InternUpdate, db: Session = Depends(get_db),
                   current_user=Depends(require_role("admin"))):
    """Admin-only. Primary use case right now: assigning a mentor to a
    student who self-registered through the landing page (their
    mentor_id starts out NULL until an admin does this)."""
    intern = db.query(Intern).filter(Intern.intern_id == intern_id).first()
    if not intern:
        raise HTTPException(status_code=404, detail="Intern not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(intern, field, value)
    db.commit()
    db.refresh(intern)
    return intern