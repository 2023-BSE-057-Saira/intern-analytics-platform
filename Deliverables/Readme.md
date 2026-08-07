# 📦 Deliverables — AI-005: Internship Performance Prediction & Risk Analytics Platform

**Ezitech Engineering Framework · Case Study AI-005**
Submitted by: **Saira Ejaz** & **Sadaf Riaz** · AI Engineers · 4-Week Sprint

This folder contains every graded deliverable for the case study, each grounded in the actual source code in this repository — not written independently of it. Where a document references a file, that file is the ground truth; the document explains it.

---

## 📋 Deliverables Checklist

| # | Deliverable | File | Status |
|---|---|---|---|
| 1 | Complete Source Code | *(repository root)* | ✅ |
| 2 | ML Pipeline | `app/ml/` | ✅ |
| 3 | Feature Engineering Documentation | [`Feature_Engineering_Documentation.pdf`](./Feature_Engineering_Documentation.pdf) | ✅ |
| 4 | Dataset Design | [`Dataset_Design.pdf`](./Dataset_Design.pdf) | ✅ |
| 5 | API Documentation | [`API_Documentation.pdf`](./API_Documentation.pdf) | ✅ |
| 6 | Model Evaluation Report | [`app/ml/saved_models/model_evaluation_report.md`](../app/ml/saved_models/model_evaluation_report.md) | ✅ |
| 7 | Explainability Report | [`Explainability_Report.pdf`](./Explainability_Report%20.pdf) | ✅ |
| 8 | Deployment Guide | [`Deployment_Guide.pdf`](./Deployment_Guide.pdf) | ✅ |
| 9 | Technical Presentation | [`Internship_Analytics_Technical_Presentation.pdf`](./Internship_Analytics_Technical_Presentation.pdf) | ✅ |
| 10 | Live Demonstration | [`Live Demo.mp4`](./Live%20Demo.mp4) | ✅ |

---

## 🧠 What's Actually in Here

**`Feature_Engineering_Documentation.pdf`** — Documents the one shared pipeline (`app/ml/features.py` + four `build_*.py` files) that turns six raw activity tables — attendance, tasks, GitHub activity, code reviews, mentor feedback, communication — into the exact feature vectors each model trains and predicts on. Covers the design principle behind keeping training and inference on one function (`build_feature_vector`), so live predictions can never silently drift from what a model was trained on.

**`Dataset_Design.pdf`** — Explains why and how the dataset is synthetic (`app/ml/generate_synthetic_data.py`, seed `42`): 800 interns across 6 technology tracks, 30 mentors, 3 batches, 90-day internship timelines — each intern driven by a hidden profile and trajectory rather than independent random fields, so the patterns are ones a model can legitimately learn.

**`API_Documentation.pdf`** — Every router actually mounted in `app/main.py` (`auth`, `admin`, `interns`, `predict`, `recommendations`, `mentor`, `students`), with JWT auth, role scoping (Admin / Mentor / Student), and ownership checks documented per endpoint. Explicitly notes that `app/routers/student.py` (singular) exists in the repo but is never imported — it's dead code, and it's correctly excluded from this doc rather than documented as if live.

**`app/ml/saved_models/model_evaluation_report.md`** — Real metrics from real test splits, not illustrative numbers:

| Model | Metric | Score |
|---|---|---|
| Dropout Risk (XGBoost) | Accuracy / ROC-AUC | 85.1% / 0.842 |
| Performance Trend (XGBoost, 3-class) | Accuracy (macro F1 83.4%) | 83.4% |
| Success Probability (XGBoost) | Accuracy / ROC-AUC | 90.5% / 0.947 |
| Learning Speed (Linear Regression) | R² | 0.594 |
| Skill Growth (Linear Regression) | R² | 0.023 *(weak — early-period signal isn't strongly predictive here; documented, not hidden)* |

**`Explainability_Report.pdf`** — Every prediction is paired with a `shap.TreeExplainer` explanation (`app/ml/predict.py`) returning the top 3 contributing features per intern, per prediction — a local explanation, not a static global importance ranking. Documents the real 3-class SHAP shape bug that was hit and fixed for the Performance Trend model, and the graceful-degradation path if SHAP computation fails.

**`Deployment_Guide.pdf`** — How the platform actually runs: FastAPI + Uvicorn on the host, PostgreSQL/Redis/MLflow/Prometheus/Grafana via Docker Compose, no separate frontend build (the `app/static/` dashboards are served directly by FastAPI).

**`Internship_Analytics_Technical_Presentation.pdf`** — 12-slide technical walkthrough: problem, architecture, models, explainability, results, live demo.

**`Live Demo.mp4`** — 3-minute recorded walkthrough of the running platform across Admin, Mentor, and Student roles.

---

## 🗂️ Also in This Folder

- **`ml.zip`** — Trained model artifacts (`.json` / `.pkl`) for all four models. These are excluded from the main repo by `.gitignore`, so this zip is what makes the platform runnable on a clean clone — extract it into `app/ml/saved_models/` before starting the API.
- **`generate_evaluation_report.py`** — Regenerates `model_evaluation_report.md` from the trained models and test split, so the metrics above can be reproduced, not just read.

---

## 🚀 Quick Start (Grader Path)

```bash
git clone https://github.com/2023-BSE-057-Saira/intern-analytics-platform.git
cd intern-analytics-platform
unzip Deliverables/ml.zip -d app/ml/saved_models/
docker compose up -d
pip install -r requirements.txt
uvicorn app.main:app --reload
```
Then open `http://localhost:8000` — dashboards for Admin, Mentor, and Student are all served from there.

---

*All figures, endpoint lists, and file references in these documents are drawn directly from the source code in this repository as of submission — not from the project description alone.*
