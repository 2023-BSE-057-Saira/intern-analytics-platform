"""
Feature Engineering Pipeline (shared across all models)
=========================================================
Converts raw DB records (attendance, tasks, github activity, code
reviews, mentor feedback, communication activity) into numeric
feature vectors that ML models can consume.

Entry points:
  1. build_feature_vector(intern_id, db)
     -> full-history features for ONE intern. Used by predict.py for
        live predictions.

  2. build_features_dataframe(db, min_days)
     -> full-history features for ALL interns, as a DataFrame. This is
        the shared base table every one of the 4 models is built from -
        each model's build_*.py file picks a different target column
        out of this table and drops whatever it doesn't need from X.

NOTE on REFERENCE_DATE:
  Using date.today() here would recompute "days since start" relative
  to whatever real-world day you happen to run training on - meaning
  the exact same database rows would produce slightly different
  feature values (and therefore slightly different model results)
  depending on when you ran the script. Pinning to a fixed
  REFERENCE_DATE (the day the current dataset was generated/imported)
  keeps results reproducible run-to-run, and keeps this file's notion
  of "today" consistent with generate_synthetic_data.py.
"""
from datetime import date

import pandas as pd
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.db_models import (
    Intern, Attendance, Task, GithubActivity, CodeReview,
    MentorFeedback, CommunicationActivity
)

# Interns younger than this (in days) don't have enough history yet
# to produce reliable features.
MIN_DAYS_FOR_TRAINING = 14

# Assumed total internship length, used to compute "how far along" an
# intern is. Must match INTERNSHIP_LENGTH_DAYS in generate_synthetic_data.py.
INTERNSHIP_LENGTH_DAYS = 90


def _get_reference_date(db: Session) -> date:
    """
    FIX: using date.today() here caused a real, hard-to-spot bug -
    two machines training on the EXACT SAME synced database on
    DIFFERENT calendar days would get different REFERENCE_DATE values,
    which changes which interns pass the MIN_DAYS_FOR_TRAINING cutoff
    AND changes the days_since_start / internship_progress_pct feature
    values for every intern - producing genuinely different results
    from identical data, with no error or warning.

    Fix: derive "today" from the data's own timeline (the latest
    attendance record on file) instead of the real-world calendar date.
    This makes results reproducible regardless of which day anyone
    actually runs training, as long as the underlying data is the same.
    """
    max_date = db.query(func.max(Attendance.date)).scalar()
    return max_date if max_date else date.today()


def _fetch_records(intern_id: int, db: Session):
    """One DB round-trip per table per intern, reused by every builder below."""
    return {
        "attendance": db.query(Attendance).filter(Attendance.intern_id == intern_id).all(),
        "tasks": db.query(Task).filter(Task.intern_id == intern_id).all(),
        "github": db.query(GithubActivity).filter(GithubActivity.intern_id == intern_id).all(),
        "reviews": db.query(CodeReview).filter(CodeReview.intern_id == intern_id).all(),
        "feedback": db.query(MentorFeedback).filter(MentorFeedback.intern_id == intern_id).all(),
        "comms": db.query(CommunicationActivity).filter(CommunicationActivity.intern_id == intern_id).all(),
    }


def _trend(records: list, date_attr: str, value_fn) -> float:
    """
    First-half vs second-half difference in value_fn's output over
    records, sorted by date_attr. Positive = improving over time,
    negative = declining.

    This closes a real gap: the data generator explicitly ties dropout
    probability to whether an intern's trajectory is declining vs
    improving (declining interns are far more likely to actually drop
    out), but until now Dropout Risk / Success Probability only saw
    flat, whole-period averages - attendance_rate tells you WHERE an
    intern has been on average, not which direction they're heading.
    An intern trending sharply downward looks identical to a
    consistently-mediocre one under averages alone, even though the
    generator treats them very differently.
    """
    if len(records) < 4:
        return 0.0
    sorted_records = sorted(records, key=lambda r: getattr(r, date_attr))
    mid = len(sorted_records) // 2
    early_vals = [value_fn(r) for r in sorted_records[:mid]]
    late_vals = [value_fn(r) for r in sorted_records[mid:]]
    early_mean = sum(early_vals) / len(early_vals) if early_vals else 0.0
    late_mean = sum(late_vals) / len(late_vals) if late_vals else 0.0
    return late_mean - early_mean


def _aggregate(records: dict) -> dict:
    """Computes the standard set of aggregate features from raw record lists."""
    attendance = records["attendance"]
    tasks = records["tasks"]
    github = records["github"]
    reviews = records["reviews"]
    feedback = records["feedback"]
    comms = records["comms"]

    total_days = len(attendance) or 1
    present_days = sum(1 for a in attendance if a.present)
    attendance_rate = present_days / total_days

    total_tasks = len(tasks) or 1
    completed_tasks = sum(1 for t in tasks if t.status == "completed")
    late_tasks = sum(1 for t in tasks if t.status == "late")
    skipped_tasks = sum(1 for t in tasks if t.status == "skipped")

    task_completion_rate = completed_tasks / total_tasks
    late_task_ratio = late_tasks / total_tasks
    skipped_task_ratio = skipped_tasks / total_tasks

    total_commits = sum(g.commits for g in github)
    total_prs = sum(g.pull_requests for g in github)
    total_issues_opened = sum(g.issues_opened for g in github)
    total_issues_closed = sum(g.issues_closed for g in github)
    active_days = len(github) or 1
    avg_commits_per_active_day = total_commits / active_days

    avg_review_score = (
        sum(float(r.score) for r in reviews if r.score is not None) / len(reviews)
        if reviews else 0.0
    )
    avg_mentor_rating = (
        sum(float(f.rating) for f in feedback if f.rating is not None) / len(feedback)
        if feedback else 0.0
    )
    avg_messages_sent = sum(c.messages_sent for c in comms) / len(comms) if comms else 0.0
    meeting_attendance_rate = sum(c.meetings_attended for c in comms) / len(comms) if comms else 0.0

    # --- Additional engineered features -----------------------------
    # These add signal beyond simple rates: consistency/volatility, and
    # difficulty-weighted performance (a stronger signal of real skill
    # than raw completion rate, which treats an easy and a hard task
    # as equally meaningful).
    review_scores = [float(r.score) for r in reviews if r.score is not None]
    review_score_std = (
        (sum((s - avg_review_score) ** 2 for s in review_scores) / len(review_scores)) ** 0.5
        if len(review_scores) > 1 else 0.0
    )

    commit_counts = [g.commits for g in github]
    avg_commit = sum(commit_counts) / len(commit_counts) if commit_counts else 0.0
    commit_std = (
        (sum((c - avg_commit) ** 2 for c in commit_counts) / len(commit_counts)) ** 0.5
        if len(commit_counts) > 1 else 0.0
    )

    hard_tasks = [t for t in tasks if t.difficulty == "hard"]
    hard_completed = sum(1 for t in hard_tasks if t.status == "completed")
    hard_task_completion_rate = hard_completed / len(hard_tasks) if hard_tasks else 0.0

    # Interaction feature: attendance and completion compound - an intern
    # who is both frequently absent AND behind on tasks is a stronger risk
    # signal than either alone (this is genuinely non-linear info a plain
    # tree split on each feature separately can miss).
    attendance_completion_interaction = attendance_rate * task_completion_rate

    # On-time ratio among tasks that were actually turned in (excludes
    # skipped) - separates "slow but reliable" from "fast but skips work".
    turned_in = completed_tasks + late_tasks
    on_time_given_turned_in = completed_tasks / turned_in if turned_in > 0 else 0.0

    # --- Trajectory features: is this intern improving or declining? ---
    # See _trend()'s docstring above for why this matters specifically
    # for Dropout Risk / Success Probability.
    attendance_trend = _trend(attendance, "date", lambda a: 1.0 if a.present else 0.0)
    completion_trend = _trend(tasks, "assigned_date", lambda t: 1.0 if t.status == "completed" else 0.0)
    review_trend = _trend(reviews, "review_date", lambda r: float(r.score) if r.score is not None else 0.0)

    return {
        "attendance_rate": attendance_rate,
        "task_completion_rate": task_completion_rate,
        "late_task_ratio": late_task_ratio,
        "skipped_task_ratio": skipped_task_ratio,
        "total_commits": total_commits,
        "total_pull_requests": total_prs,
        "total_issues_opened": total_issues_opened,
        "total_issues_closed": total_issues_closed,
        "avg_commits_per_active_day": avg_commits_per_active_day,
        "avg_code_review_score": avg_review_score,
        "review_score_std": review_score_std,
        "commit_std": commit_std,
        "hard_task_completion_rate": hard_task_completion_rate,
        "attendance_completion_interaction": attendance_completion_interaction,
        "on_time_given_turned_in": on_time_given_turned_in,
        "avg_mentor_rating": avg_mentor_rating,
        "avg_messages_sent": avg_messages_sent,
        "meeting_attendance_rate": meeting_attendance_rate,
        "attendance_trend": attendance_trend,
        "completion_trend": completion_trend,
        "review_trend": review_trend,
    }


def build_feature_vector(intern_id: int, db: Session, reference_date: date = None) -> dict:
    """Full-history feature vector for ONE intern (Dropout Risk / Success Probability)."""
    intern = db.query(Intern).filter(Intern.intern_id == intern_id).first()
    records = _fetch_records(intern_id, db)
    features = _aggregate(records)

    if reference_date is None:
        # No reference_date given (e.g. a live prediction via predict.py) -
        # real-world "today" is the correct meaning in that case, since
        # we're asking "how is this intern doing as of right now".
        reference_date = date.today()

    days_since_start = (reference_date - intern.start_date).days if intern else 0
    internship_progress_pct = min(1.0, days_since_start / INTERNSHIP_LENGTH_DAYS)

    features["days_since_start"] = days_since_start
    features["internship_progress_pct"] = internship_progress_pct
    return features


def build_features_dataframe(db: Session, min_days: int = MIN_DAYS_FOR_TRAINING) -> pd.DataFrame:
    """
    Full-history feature table for ALL interns. Shared base table used
    by every model's build_*.py file (each one picks a different
    target column from here and drops what it doesn't need from X).
    """
    reference_date = _get_reference_date(db)
    interns = db.query(Intern).all()
    rows = []

    for intern in interns:
        days_since_start = (reference_date - intern.start_date).days
        if days_since_start < min_days:
            continue

        features = build_feature_vector(intern.intern_id, db, reference_date=reference_date)
        row = {
            "intern_id": intern.intern_id,
            "technology": intern.technology,
            "status": intern.status,
            "dropped": 1 if intern.status == "dropped" else 0,
            "completed": 1 if intern.status == "completed" else 0,
            **features,
        }
        rows.append(row)

    df = pd.DataFrame(rows)
    if not df.empty:
        df = pd.get_dummies(df, columns=["technology"], prefix="tech")
    return df


if __name__ == "__main__":
    # Quick manual check: `python -m app.ml.features`
    from app.database import SessionLocal

    db = SessionLocal()
    full_df = build_features_dataframe(db)
    db.close()

    print(f"Full-history feature table: {full_df.shape[0]} rows, {full_df.shape[1]} cols")
    print("Label balance (dropped):")
    print(full_df["dropped"].value_counts())