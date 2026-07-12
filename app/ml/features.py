"""
Feature Engineering Pipeline
Converts raw DB records (attendance, tasks, github activity, etc.)
into a numeric feature vector a model can consume.

WEEK 2 TODO: flesh this out with real aggregations, e.g.:
  - attendance_rate = present_days / total_days
  - avg_task_completion_time
  - commits_per_week
  - avg_code_review_score
  - mentor_feedback_avg_rating
"""
from sqlalchemy.orm import Session
from app.models.db_models import Attendance, Task, GithubActivity, CodeReview, MentorFeedback


def build_feature_vector(intern_id: int, db: Session) -> dict:
    """Returns a dict of engineered features for a single intern."""

    attendance_records = db.query(Attendance).filter(Attendance.intern_id == intern_id).all()
    tasks = db.query(Task).filter(Task.intern_id == intern_id).all()
    github = db.query(GithubActivity).filter(GithubActivity.intern_id == intern_id).all()
    reviews = db.query(CodeReview).filter(CodeReview.intern_id == intern_id).all()
    feedback = db.query(MentorFeedback).filter(MentorFeedback.intern_id == intern_id).all()

    total_days = len(attendance_records) or 1
    present_days = sum(1 for a in attendance_records if a.present)
    attendance_rate = present_days / total_days

    total_tasks = len(tasks) or 1
    completed_tasks = sum(1 for t in tasks if t.status == "completed")
    task_completion_rate = completed_tasks / total_tasks

    total_commits = sum(g.commits for g in github)
    total_prs = sum(g.pull_requests for g in github)

    avg_review_score = (
        sum(float(r.score) for r in reviews if r.score is not None) / len(reviews)
        if reviews else 0.0
    )
    avg_mentor_rating = (
        sum(float(f.rating) for f in feedback if f.rating is not None) / len(feedback)
        if feedback else 0.0
    )

    return {
        "attendance_rate": attendance_rate,
        "task_completion_rate": task_completion_rate,
        "total_commits": total_commits,
        "total_pull_requests": total_prs,
        "avg_code_review_score": avg_review_score,
        "avg_mentor_rating": avg_mentor_rating,
    }
