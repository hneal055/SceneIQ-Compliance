# ========================================
# Multi-stage build for SceneIQ
# Python 3.12 + FastAPI + React Frontend
# ========================================

# Stage 0: Frontend Builder
FROM node:20-slim AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Stage 1: Python Builder
FROM python:3.12-slim AS builder
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    make \
    postgresql-client \
    libatomic1 \
    && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt
COPY prisma ./prisma
RUN python -m prisma generate && \
    python -m prisma py fetch

# Stage 2: Runtime
FROM python:3.12-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql-client \
    libatomic1 \
    && rm -rf /var/lib/apt/lists/*
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY --from=builder /root/.cache /root/.cache
ARG CACHEBUST=1
COPY . .
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist
ENV PRISMA_PYTHON_BINARY_CACHE_DIR=/root/.cache/prisma-python
ENV XDG_CACHE_HOME=/root/.cache
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health', timeout=5)"
CMD ["sh", "-c", "uvicorn src.main:app --host 0.0.0.0 --port \"]
