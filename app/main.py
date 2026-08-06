"""
Main FastAPI application — AI-Powered Internship Performance
Prediction & Risk Analytics Platform (Ezitech Case Study AI-005)
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from prometheus_fastapi_instrumentator import Instrumentator

from app.database import Base, engine
from app.routers import admin, auth, interns, mentor, predictions, recommendations, students


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

app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(interns.router)
app.include_router(predictions.router)
app.include_router(recommendations.router)
app.include_router(mentor.router)
app.include_router(students.router)

Instrumentator().instrument(app).expose(app)

# --- Static assets (css/js) ------------------------------------------------
# Served under /static, e.g. /static/css/base.css, /static/js/auth.js
app.mount("/static", StaticFiles(directory="app/static"), name="static")


# --- Page routes -------------------------------------------------------------
@app.get("/")
def serve_root():
    return FileResponse("app/static/index.html")


@app.get("/login")
def serve_login():
    return FileResponse("app/static/login.html")


@app.get("/admin")
def serve_admin():
    return FileResponse("app/static/admin.html")


@app.get("/register")
def serve_register():
    # No separate register.html — the signup flow lives as a tab
    # inside login.html (Sign In / Create Student Account). This route
    # just gives it a friendlier landing-page link.
    return FileResponse("app/static/login.html")


@app.get("/mentor")
def serve_mentor():
    return FileResponse("app/static/mentor.html")


@app.get("/student")
def serve_student():
    return FileResponse("app/static/student.html")


@app.get("/settings")
def serve_settings():
    return FileResponse("app/static/settings.html")


@app.get("/intern/{intern_id}")
def serve_intern_detail(intern_id: int):
    return FileResponse("app/static/intern-detail.html")


@app.get("/risk-alerts")
def serve_mentor_risk_alerts():
    # NOTE: intentionally NOT /mentor/risk-alerts — that path is already
    # claimed by the mentor API router's GET /mentor/risk-alerts (JSON
    # endpoint), registered earlier in this file. Routes are matched in
    # registration order, so reusing that path here would silently
    # shadow one of the two and break it.
    return FileResponse("app/static/risk-alerts.html")


@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "healthy"}