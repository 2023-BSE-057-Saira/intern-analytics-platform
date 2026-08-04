"""
Batch Prediction Runner
==========================
The dashboard reads predictions from the `predictions` table (fast,
no live model calls needed while browsing). This script runs all 6
predictions for every active intern and saves the results, so the
dashboard has real data to show.

Run this once after training/retraining models, or periodically to
refresh predictions (e.g. daily) - not on every dashboard page view.

Usage:
    python -m app.ml.batch_predict
"""
from app.database import SessionLocal
from app.models.db_models import Intern, Prediction
from app.ml.predict import (
    predict_dropout_risk, predict_performance_trend, predict_success_probability,
    predict_learning_growth, predict_completion_probability, predict_project_success_probability,
)


def save_prediction(db, intern_id, prediction_type, result):
    record = Prediction(
        intern_id=intern_id,
        prediction_type=prediction_type,
        predicted_value=result["value"],
        confidence=result.get("confidence"),
        explanation_json=result.get("explanation"),
    )
    db.add(record)


def main():
    db = SessionLocal()
    interns = db.query(Intern).filter(Intern.status == "active").all()
    print(f"Running predictions for {len(interns)} active interns...")

    success_count = 0
    error_count = 0

    for i, intern in enumerate(interns):
        try:
            dropout = predict_dropout_risk(intern.intern_id, db)
            save_prediction(db, intern.intern_id, "dropout_risk", dropout)

            trend = predict_performance_trend(intern.intern_id, db)
            save_prediction(db, intern.intern_id, "performance_trend", trend)

            success = predict_success_probability(intern.intern_id, db)
            save_prediction(db, intern.intern_id, "success_probability", success)

            growth = predict_learning_growth(intern.intern_id, db)
            save_prediction(db, intern.intern_id, "learning_speed", growth)
            skill_growth_result = {
                "value": growth["explanation"]["skill_growth"],
                "confidence": None,
                "explanation": growth["explanation"],
            }
            save_prediction(db, intern.intern_id, "skill_growth", skill_growth_result)

            completion = predict_completion_probability(intern.intern_id, db)
            save_prediction(db, intern.intern_id, "completion_probability", completion)

            project_success = predict_project_success_probability(intern.intern_id, db)
            save_prediction(db, intern.intern_id, "project_success_probability", project_success)

            success_count += 1
            if (i + 1) % 20 == 0:
                db.commit()
                print(f"  ...{i + 1}/{len(interns)} interns processed")

        except Exception as e:
            error_count += 1
            print(f"  ERROR on intern {intern.intern_id}: {type(e).__name__}: {e}")

    db.commit()
    db.close()
    print(f"\nDone. {success_count} interns processed successfully, {error_count} errors.")


if __name__ == "__main__":
    main()
