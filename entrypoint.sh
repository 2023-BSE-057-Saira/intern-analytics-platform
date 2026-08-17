#!/bin/sh
set -e

# ---------------------------------------------------------------------------
# 1. Unpack trained models (ml.zip -> app/ml/saved_models/*.json/.pkl)
#    Skip if already extracted (e.g. re-deploy without image rebuild).
# ---------------------------------------------------------------------------
if [ ! -f "app/ml/saved_models/dropout_risk_xgb.json" ]; then
  echo ">> Extracting trained models from app/ml.zip ..."
  unzip -o app/ml.zip -d app/ >/dev/null
else
  echo ">> Trained models already present, skipping unzip."
fi

# ---------------------------------------------------------------------------
# 2. Restore the database ONLY if it's empty (custom-format pg_dump already
#    contains full schema + data - no need to separately run schema.sql or
#    the migration files, restoring the dump alone recreates everything).
#    We check for the 'interns' table as a marker of "already restored".
# ---------------------------------------------------------------------------
if [ -n "$DATABASE_URL" ]; then
  echo ">> Waiting for Postgres to accept connections ..."
  for i in $(seq 1 30); do
    pg_isready -d "$DATABASE_URL" >/dev/null 2>&1 && break
    sleep 2
  done

  TABLE_EXISTS=$(psql "$DATABASE_URL" -tAc "SELECT to_regclass('public.interns');" 2>/dev/null || echo "")
  if [ "$TABLE_EXISTS" = "interns" ]; then
    echo ">> Database already populated (interns table exists), skipping restore."
  elif [ -f "data_export.dump" ]; then
    echo ">> Empty database detected - restoring data_export.dump ..."
    pg_restore --no-owner --no-privileges --clean --if-exists -d "$DATABASE_URL" data_export.dump || \
      echo ">> pg_restore finished with warnings (usually harmless on a fresh DB)."
  else
    echo ">> No data_export.dump found - starting with an empty schema."
  fi
else
  echo ">> WARNING: DATABASE_URL is not set. Skipping DB restore; app will fail to connect."
fi

# ---------------------------------------------------------------------------
# 3. Start the API
# ---------------------------------------------------------------------------
echo ">> Starting FastAPI on port ${PORT:-8000} ..."
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
