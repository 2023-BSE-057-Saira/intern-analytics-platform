"""
Main FastAPI application — AI-Powered Internship Performance
Prediction & Risk Analytics Platform (Ezitech Case Study AI-005)
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

from app.database import Base, engine
from app.routers import interns, predictions, recommendations

# Creates tables if they don't already exist (schema.sql handles first-run via Docker,
# this is a safety net for local/dev runs)
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Internship Performance Prediction & Risk Analytics API",
    description="AI-powered platform for predicting intern performance, dropout risk, "
                 "and generating personalized recommendations.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten this before real deployment
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(interns.router)
app.include_router(predictions.router)
app.include_router(recommendations.router)

# Exposes /metrics for Prometheus to scrape
Instrumentator().instrument(app).expose(app)


@app.get("/", tags=["Health"])
def root():
    return {"status": "ok", "service": "intern-analytics-platform"}


@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "healthy"}
