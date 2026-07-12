# Internship Performance Prediction & Risk Analytics Platform

Ezitech Case Study AI-005 — AI-powered platform that predicts intern
performance, dropout risk, and generates personalized recommendations.

## Project Structure

```
intern-analytics-platform/
├── docker-compose.yml       # Postgres, Redis, MLflow, Prometheus, Grafana
├── requirements.txt         # Python dependencies
├── .env.example              # Copy to .env
├── sql/
│   └── schema.sql            # Auto-loaded into Postgres on first run
├── monitoring/
│   └── prometheus.yml
└── app/
    ├── main.py                # FastAPI entrypoint
    ├── database.py             # DB connection/session
    ├── models/db_models.py     # SQLAlchemy ORM models
    ├── schemas/schemas.py      # Pydantic request/response models
    ├── routers/                # API endpoints
    │   ├── interns.py
    │   ├── predictions.py
    │   └── recommendations.py
    ├── ml/
    │   ├── features.py         # Feature engineering pipeline
    │   ├── train.py             # Model training script (Week 2)
    │   ├── predict.py           # Prediction engine (currently placeholder logic)
    │   └── saved_models/        # Trained models get saved here
    └── services/
        └── recommendation_engine.py  # Rule-based recommendation logic
```

## Setup

### 1. Start infrastructure (Postgres, Redis, MLflow, Prometheus, Grafana)

```bash
docker-compose up -d
```

Check everything is running:

```bash
docker ps
```

You should see 5 containers: `intern_postgres`, `intern_redis`,
`intern_mlflow`, `intern_prometheus`, `intern_grafana`.

### 2. Set up Python environment

```bash
python -m venv venv
venv\Scripts\activate          # Windows
python -m pip install -r requirements.txt
```

### 3. Configure environment variables

```bash
copy .env.example .env
```

### 4. Run the API

```bash
uvicorn app.main:app --reload
```

- API docs (Swagger): http://localhost:8000/docs
- Health check: http://localhost:8000/health

### 5. Access supporting services

| Service | URL | Credentials |
|---|---|---|
| API Docs | http://localhost:8000/docs | — |
| MLflow | http://localhost:5000 | — |
| Prometheus | http://localhost:9090 | — |
| Grafana | http://localhost:3000 | admin / admin123 |
| Postgres | localhost:5432 | intern_admin / intern_pass123 |

Connect to Postgres from **DBeaver** using the credentials above to
browse tables visually.

## Current Status

- [x] Database schema designed (`sql/schema.sql`)
- [x] Docker Compose infrastructure
- [x] FastAPI skeleton with routers for interns/predictions/recommendations
- [x] Feature engineering pipeline (basic aggregations)
- [ ] Synthetic dataset generation (Week 1, Day 3)
- [ ] Model training — dropout risk, performance trend, success probability (Week 2)
- [ ] SHAP explainability integration (Week 3)
- [ ] Dashboard — Admin / Mentor / Student views (Week 4)

## Notes

- `app/ml/predict.py` currently returns **placeholder/dummy predictions**
  so the API is fully testable end-to-end via Postman before real
  models exist. Replace with actual model loading once Week 2 training
  is complete.
- `app/ml/train.py` has a `load_training_data()` stub that needs to be
  connected to the synthetic dataset once it's generated.
