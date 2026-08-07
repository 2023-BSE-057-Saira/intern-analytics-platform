# Deploy-only Dockerfile — builds just the FastAPI app.
# Redis/MLflow/Prometheus/Grafana from docker-compose.yml are dev-only
# extras your code doesn't actually depend on to run.

FROM python:3.12-slim

WORKDIR /app

# build-essential covers xgboost/lightgbm's native bits if a prebuilt
# wheel isn't available for the platform Railway builds on
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Railway sets $PORT at runtime — don't hardcode 8000
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
