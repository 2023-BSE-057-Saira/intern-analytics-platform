"""
Build Success Probability Dataset
====================================
Unlike Dropout Risk (which predicts "did they leave?"), Success
Probability predicts something more meaningful: "will this intern
complete the internship AND perform well?" An intern who barely
finishes with poor reviews isn't really a success story - so we
define success as completion + above-median performance.

Label:
    success = 1  if status == 'completed' AND avg_review_score >= median
    success = 0  otherwise (dropped, or completed but underperformed)

Usage:
    from app.ml.build_success_dataset import build_success_dataset
    df = build_success_dataset()
"""
import pandas as pd
from sqlalchemy import text
from app.database import engine


def build_success_dataset() -> pd.DataFrame:
    interns = pd.read_sql(text("SELECT * FROM interns"), engine)
    attendance = pd.read_sql(text("SELECT * FROM attendance"), engine)
    tasks = pd.read_sql(text("SELECT * FROM tasks"), engine)
    github = pd.read_sql(text("SELECT * FROM github_activity"), engine)
    reviews = pd.read_sql(text("SELECT * FROM code_reviews"), engine)
    feedback = pd.read_sql(text("SELECT * FROM mentor_feedback"), engine)
    comms = pd.read_sql(text("SELECT * FROM communication_activity"), engine)

    # --- Aggregate each table to one row per intern ---
    attendance_agg = attendance.groupby("intern_id").agg(
        attendance_rate=("present", "mean")
    ).reset_index()

    tasks_agg = tasks.groupby("intern_id").agg(
        total_tasks=("task_id", "count"),
        completed_tasks=("status", lambda s: (s == "completed").sum()),
        late_tasks=("status", lambda s: (s == "late").sum()),
        skipped_tasks=("status", lambda s: (s == "skipped").sum()),
    ).reset_index()
    tasks_agg["task_completion_rate"] = tasks_agg["completed_tasks"] / tasks_agg["total_tasks"]

    github_agg = github.groupby("intern_id").agg(
        total_commits=("commits", "sum"),
        total_prs=("pull_requests", "sum"),
    ).reset_index()

    reviews_agg = reviews.groupby("intern_id").agg(
        avg_review_score=("score", "mean"),
        num_reviews=("review_id", "count"),
    ).reset_index()

    feedback_agg = feedback.groupby("intern_id").agg(
        avg_mentor_rating=("rating", "mean"),
    ).reset_index()

    comms_agg = comms.groupby("intern_id").agg(
        total_messages=("messages_sent", "sum"),
        total_meetings=("meetings_attended", "sum"),
    ).reset_index()

    # --- Merge onto interns ---
    df = interns[["intern_id", "technology", "status"]].copy()
    df = df.merge(attendance_agg, on="intern_id", how="left")
    df = df.merge(tasks_agg[["intern_id", "task_completion_rate", "late_tasks", "skipped_tasks"]],
                   on="intern_id", how="left")
    df = df.merge(github_agg, on="intern_id", how="left")
    df = df.merge(reviews_agg, on="intern_id", how="left")
    df = df.merge(feedback_agg, on="intern_id", how="left")
    df = df.merge(comms_agg, on="intern_id", how="left")

    # --- Handle missing values ---
    numeric_defaults = {
        "attendance_rate": 0.0, "task_completion_rate": 0.0,
        "late_tasks": 0, "skipped_tasks": 0,
        "total_commits": 0, "total_prs": 0,
        "avg_review_score": 0.0, "num_reviews": 0,
        "avg_mentor_rating": 0.0,
        "total_messages": 0, "total_meetings": 0,
    }
    df = df.fillna(numeric_defaults)

    # --- Only use interns with a KNOWN outcome (same reasoning as Model 1) ---
    df = df[df["status"].isin(["dropped", "completed"])].copy()

    # --- Build the label ---
    # Median is computed only among COMPLETED interns, since that's the
    # relevant comparison group for "did well vs did poorly" - comparing
    # a dropped intern's (often lower) score would skew the threshold.
    completed_scores = df.loc[df["status"] == "completed", "avg_review_score"]
    median_score = completed_scores.median()
    print(f"Median review score among completed interns: {median_score:.2f}")

    df["success"] = (
        (df["status"] == "completed") & (df["avg_review_score"] >= median_score)
    ).astype(int)

    # --- Encode categorical + finalize feature set ---
    df = pd.get_dummies(df, columns=["technology"], prefix="tech")
    df = df.drop(columns=["status"])

    # IMPORTANT: drop avg_review_score from the FEATURES. It was used to
    # construct the label itself (success = completed AND score >= median),
    # so leaving it in as a feature would let the model "cheat" by just
    # reading the answer directly instead of learning genuine behavioral
    # patterns (attendance, task completion, commits, etc.).
    df = df.drop(columns=["avg_review_score"])

    return df


if __name__ == "__main__":
    dataset = build_success_dataset()
    print(f"Dataset shape: {dataset.shape}")
    print(f"\nColumns: {list(dataset.columns)}")
    print(f"\nLabel balance:\n{dataset['success'].value_counts()}")
    print(f"\nFirst few rows:\n{dataset.head()}")