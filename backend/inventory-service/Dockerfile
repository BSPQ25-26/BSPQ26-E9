# ─────────────────────────────────────────────
#  Wallabot — inventory-service Dockerfile
#  Multi-stage: builder + lean runtime image
#  SQLite now, Supabase-ready later
# ─────────────────────────────────────────────


# ── inventory-service Dockerfile ──
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# curl is needed for the Docker healthcheck
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY . /app

# Ensure the SQLite data directory exists
RUN mkdir -p /app/data

EXPOSE 8000

# Ajusta el CMD según tu entrypoint real
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]


CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]