# =============================
# 🌱  BASE IMAGE
# =============================
FROM python:3.11-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=100 \
    PATH="/root/.local/bin:$PATH"

WORKDIR /app

# Dependencies (shared for dev & prod)
COPY requirements.txt .
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    poppler-utils \
    && pip install --upgrade pip \
    && pip install -r requirements.txt \
    && apt-get remove -y build-essential \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

COPY . .

# =============================
# 🧑‍💻 DEVELOPMENT STAGE
# =============================
FROM base AS dev

ENV ENVIRONMENT=development

# Enable live reload
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080", "--reload"]

# =============================
# 🏭 PRODUCTION STAGE
# =============================
FROM base AS prod

# Cleanup extra build deps and caches (non-fatal purge)
RUN (pip cache purge || true) && rm -rf /root/.cache /root/.local/share

ENV ENVIRONMENT=production

# Use gunicorn (multi-worker, stable)
CMD ["gunicorn", "-k", "uvicorn.workers.UvicornWorker", "app.main:app", "--bind", "0.0.0.0:8080", "--workers", "4"]