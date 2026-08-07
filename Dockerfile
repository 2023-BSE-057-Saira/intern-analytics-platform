FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

# Shell form (no brackets) is required here — Railway assigns a dynamic
# port via the PORT env var, and only shell form runs the command
# through /bin/sh, which is what actually expands ${PORT}. Exec/JSON-array
# form (CMD ["uvicorn", ...]) does NOT expand env vars — it passes
# "${PORT:-8000}" to uvicorn as a literal, broken string.
# :-8000 is just a local fallback for `docker run` without Railway.
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}