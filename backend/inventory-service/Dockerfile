# ─────────────────────────────────────────────
#  Wallabot — inventory-service Dockerfile
#  Multi-stage: builder + lean runtime image
#  SQLite now, Supabase-ready later
# ─────────────────────────────────────────────

# ── Stage 1: builder ─────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /build

# Install dependencies into an isolated prefix
# so Stage 2 can copy only what it needs
COPY requirements.txt .
RUN pip install --upgrade pip \
    && pip install --prefix=/install --no-cache-dir -r requirements.txt


# ── Stage 2: runtime ─────────────────────────
FROM python:3.11-slim AS runtime

# curl is needed for the Docker healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy application source
COPY ./app ./app

# Ensure the SQLite data directory exists
# (will be overridden by the volume mount in compose)
RUN mkdir -p /app/data

# Expose FastAPI default port
EXPOSE 8000


CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]