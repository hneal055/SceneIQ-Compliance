# ========================================
# Multi-stage build for SceneIQ
# Python 3.12 + FastAPI
# ========================================

# Stage 1: Builder
FROM python:3.12-slim as builder

WORKDIR /app

# Install system dependencies including libatomic1 and build essentials
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    make \
    postgresql-client \
    libatomic1 \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy Prisma schema
COPY prisma ./prisma

# Generate Prisma client and fetch binaries
RUN python -m prisma generate && \
    python -m prisma py fetch

# ========================================
# Stage 2: Runtime
FROM python:3.12-slim

WORKDIR /app

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql-client \
    libatomic1 \
    && rm -rf /var/lib/apt/lists/*

# Copy Python packages from builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy Prisma binaries and cache from builder (only /root/.cache exists)
COPY --from=builder /root/.cache /root/.cache

# Copy application code
ARG CACHEBUST=1
COPY . .

# Set Prisma cache environment variables to use /root/.cache
ENV PRISMA_PYTHON_BINARY_CACHE_DIR=/root/.cache/prisma-python
ENV XDG_CACHE_HOME=/root/.cache

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health', timeout=5)"

# Start application
CMD ["sh", "-c", "uvicorn src.main:app --host 0.0.0.0 --port ${PORT:-8000}"]

