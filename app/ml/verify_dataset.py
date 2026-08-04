"""
Dataset Verification Script
==============================
Run this on both team members' machines and compare the printed
output. If you both generated data using the same script (with the
fixed random seed), these numbers should match exactly.

Usage:
    python -m app.ml.verify_dataset
"""
import hashlib
import pandas as pd
from sqlalchemy import text
from app.database import engine

TABLES = [
    "interns", "attendance", "tasks", "github_activity",
    "code_reviews", "mentor_feedback", "communication_activity", "mentors"
]


def main():
    print("=" * 60)
    print("DATASET VERIFICATION REPORT")
    print("=" * 60)

    # --- Row counts per table ---
    print("\n--- Row counts per table ---")
    for table in TABLES:
        count = pd.read_sql(text(f"SELECT COUNT(*) as c FROM {table}"), engine)["c"][0]
        print(f"  {table:30s} {count}")

    # --- Status distribution ---
    print("\n--- Intern status distribution ---")
    status_dist = pd.read_sql(
        text("SELECT status, COUNT(*) as count FROM interns GROUP BY status ORDER BY status"),
        engine
    )
    print(status_dist.to_string(index=False))

    # --- Technology distribution ---
    print("\n--- Technology distribution ---")
    tech_dist = pd.read_sql(
        text("SELECT technology, COUNT(*) as count FROM interns GROUP BY technology ORDER BY technology"),
        engine
    )
    print(tech_dist.to_string(index=False))

    # --- Checksum of key intern data (exact match check) ---
    print("\n--- Checksum verification ---")
    interns = pd.read_sql(
        text("SELECT intern_id, name, email, technology, status FROM interns ORDER BY intern_id"),
        engine
    )
    interns_str = interns.to_csv(index=False)
    checksum = hashlib.md5(interns_str.encode()).hexdigest()
    print(f"  Interns table checksum: {checksum}")
    print("  (If this matches your teammate's checksum EXACTLY, your data is identical)")

    # --- First and last 3 interns (quick visual spot-check) ---
    print("\n--- First 3 interns ---")
    print(interns.head(3).to_string(index=False))
    print("\n--- Last 3 interns ---")
    print(interns.tail(3).to_string(index=False))

    print("\n" + "=" * 60)
    print("Send this ENTIRE output to your teammate and compare side by side.")
    print("=" * 60)


if __name__ == "__main__":
    main()
