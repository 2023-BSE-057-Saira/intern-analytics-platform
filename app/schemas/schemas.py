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
