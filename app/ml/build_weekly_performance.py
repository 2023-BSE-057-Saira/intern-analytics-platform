"""
Build Weekly Performance Table
=================================
Reads existing attendance/tasks/github/reviews data and summarizes it
into a week-by-week snapshot per intern. This is a DERIVED table -
it only reads data that's already in the database, so running this
does NOT touch or regenerate any of your core synthetic data.

Run this AFTER generate_synthetic_data.py.

Usage:
    python -m app.ml.build_weekly_performance
"""
import pandas as pd
from sqlalchemy import text
from app.database import engine


def main():
    print("Reading existing data...")
    interns = pd.read_sql(text("SELECT intern_id, start_date FROM interns"), engine)
    attendance = pd.read_sql(text("SELECT intern_id, date, present FROM attendance"), engine)
    tasks = pd.read_sql(text("SELECT intern_id, assigned_date, status FROM tasks"), engine)
    github = pd.read_sql(text("SELECT intern_id, date, commits FROM github_activity"), engine)
    reviews = pd.read_sql(text("SELECT intern_id, review_date, score FROM code_reviews"), engine)

    attendance["present_numeric"] = attendance["present"].astype(int)
    tasks["completed_numeric"] = (tasks["status"] == "completed").astype(int)

    # IMPORTANT: Postgres DATE columns come back from pd.read_sql as plain
    # Python date objects (dtype 'object'), which do NOT support .dt
    # accessor or vectorized subtraction. Must convert explicitly first.
    for df in (interns, attendance, tasks, github, reviews):
        for col in ("start_date", "date", "assigned_date", "review_date"):
            if col in df.columns:
                df[col] = pd.to_datetime(df[col])

    # Merge each intern's start_date in, to compute week_number relative
    # to when THEY started (not a shared calendar week).
    attendance = attendance.merge(interns, on="intern_id")
    tasks = tasks.merge(interns, on="intern_id")
    github = github.merge(interns, on="intern_id")
    reviews = reviews.merge(interns, on="intern_id")

    attendance["week_number"] = ((attendance["date"] - attendance["start_date"]).dt.days // 7) + 1
    tasks["week_number"] = ((tasks["assigned_date"] - tasks["start_date"]).dt.days // 7) + 1
    github["week_number"] = ((github["date"] - github["start_date"]).dt.days // 7) + 1
    reviews["week_number"] = ((reviews["review_date"] - reviews["start_date"]).dt.days // 7) + 1

    print("Aggregating by intern + week...")
    attendance_weekly = attendance.groupby(["intern_id", "week_number"]).agg(
        attendance_rate=("present_numeric", "mean")
    ).reset_index()

    tasks_weekly = tasks.groupby(["intern_id", "week_number"]).agg(
        task_completion_rate=("completed_numeric", "mean")
    ).reset_index()

    github_weekly = github.groupby(["intern_id", "week_number"]).agg(
        avg_commits=("commits", "mean")
    ).reset_index()

    reviews_weekly = reviews.groupby(["intern_id", "week_number"]).agg(
        avg_review_score=("score", "mean")
    ).reset_index()

    # --- Combine into one row per intern per week ---
    weekly = attendance_weekly.merge(tasks_weekly, on=["intern_id", "week_number"], how="outer")
    weekly = weekly.merge(github_weekly, on=["intern_id", "week_number"], how="outer")
    weekly = weekly.merge(reviews_weekly, on=["intern_id", "week_number"], how="outer")
    weekly = weekly.merge(interns, on="intern_id", how="left")

    weekly["week_start_date"] = weekly["start_date"] + pd.to_timedelta((weekly["week_number"] - 1) * 7, unit="D")
    weekly = weekly.drop(columns=["start_date"])
    weekly = weekly[weekly["week_number"] >= 1]  # safety: drop any stray negative/zero weeks

    print(f"Generated {len(weekly)} weekly snapshot rows across all interns.")

    print("Writing to weekly_performance table...")
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM weekly_performance"))  # safe to re-run
        weekly.to_sql("weekly_performance", conn, if_exists="append", index=False)

    print("Done. weekly_performance table populated.")


if __name__ == "__main__":
    main()
