FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    unzip \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN echo "cache bust 1"
RUN chmod +x entrypoint.sh

EXPOSE 8000

# entrypoint.sh handles, in order: unzipping app/ml.zip into
# app/ml/saved_models/ (trained model artifacts, gitignored as binaries),
# restoring data_export.dump into Postgres if the DB is empty (the dump
# is a full pg_dump -Fc, schema + data - no separate schema.sql/migration
# run needed), then finally starting uvicorn on Railway/Render's dynamic
# $PORT. All idempotent, so re-deploys without a fresh DB are safe.
CMD ["./entrypoint.sh"]