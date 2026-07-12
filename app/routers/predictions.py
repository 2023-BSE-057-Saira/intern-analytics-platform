"""
Endpoints that trigger and retrieve ML predictions.

NOTE: The actual model-loading logic goes in app/ml/predict.py.
This router just wires the HTTP layer to it — fill in ml/predict.py
once your models from Week 2 are trained and saved.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.db_models import Intern, Prediction
from app.schemas.schemas import PredictionOut, PredictionRequest
from app.ml.predict import predict_dropout_risk, predict_performance_trend, predict_success_probability

router = APIRouter(prefix="/predict", tags=["Predictions"])


@router.post("/dropout-risk", response_model=PredictionOut)
def get_dropout_risk(req: PredictionRequest, db: Session = Depends(get_db)):
    intern = db.query(Intern).filter(Intern.intern_id == req.intern_id).first()
    if not intern:
        raise HTTPException(status_code=404, detail="Intern not found")

    result = predict_dropout_risk(intern_id=req.intern_id, db=db)

    record = Prediction(
        intern_id=req.intern_id,
        prediction_type="dropout_risk",
        predicted_value=result["value"],
        confidence=result.get("confidence"),
        explanation_json=result.get("explanation"),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return PredictionOut(
        intern_id=record.intern_id,
        prediction_type=record.prediction_type,
        predicted_value=float(record.predicted_value),
        confidence=float(record.confidence) if record.confidence else None,
        explanation=record.explanation_json,
        created_at=record.created_at,
    )


@router.post("/performance-trend", response_model=PredictionOut)
def get_performance_trend(req: PredictionRequest, db: Session = Depends(get_db)):
    intern = db.query(Intern).filter(Intern.intern_id == req.intern_id).first()
    if not intern:
        raise HTTPException(status_code=404, detail="Intern not found")

    result = predict_performance_trend(intern_id=req.intern_id, db=db)

    record = Prediction(
        intern_id=req.intern_id,
        prediction_type="performance_trend",
        predicted_value=result["value"],
        confidence=result.get("confidence"),
        explanation_json=result.get("explanation"),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@router.post("/success-probability", response_model=PredictionOut)
def get_success_probability(req: PredictionRequest, db: Session = Depends(get_db)):
    intern = db.query(Intern).filter(Intern.intern_id == req.intern_id).first()
    if not intern:
        raise HTTPException(status_code=404, detail="Intern not found")

    result = predict_success_probability(intern_id=req.intern_id, db=db)

    record = Prediction(
        intern_id=req.intern_id,
        prediction_type="success_probability",
        predicted_value=result["value"],
        confidence=result.get("confidence"),
        explanation_json=result.get("explanation"),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@router.get("/history/{intern_id}", response_model=list[PredictionOut])
def prediction_history(intern_id: int, db: Session = Depends(get_db)):
    records = db.query(Prediction).filter(Prediction.intern_id == intern_id).all()
    return [
        PredictionOut(
            intern_id=r.intern_id,
            prediction_type=r.prediction_type,
            predicted_value=float(r.predicted_value),
            confidence=float(r.confidence) if r.confidence else None,
            explanation=r.explanation_json,
            created_at=r.created_at,
        )
        for r in records
    ]
