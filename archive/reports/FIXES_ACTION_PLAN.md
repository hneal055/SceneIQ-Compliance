# Container & UI Image Fixes - Action Plan

## 🎯 Fix #1: Frontend Health Check (CRITICAL)

### Problem
desksos-enterprise-client container marked "unhealthy" because curl is missing.

### Solution - Create Patch for desksos-enterprise-client

Since you're using a pre-built image, create a wrapper Dockerfile or update the source:

**Option A: Dockerfile to wrap existing image with curl**
```dockerfile
# File: Dockerfile.frontend-patch
FROM desksos-enterprise-client:latest

# Install curl for health checks
RUN apt-get update && apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:3000 || exit 1
```

**Build & Run**:
```bash
docker build -f Dockerfile.frontend-patch -t desksos-enterprise-client:healthy .
docker tag desksos-enterprise-client:healthy desksos-enterprise-client:latest
```

**Option B: Replace with wget-based health check**
If modifying the image directly, use:
```dockerfile
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD wget -q -O - http://localhost:3000 > /dev/null || exit 1
```

---

## 🎯 Fix #2: Create Frontend Dockerfile (CRITICAL)

### Current Problem
- Frontend only works with pre-built ./frontend/dist
- No automated build in docker-compose pipeline
- Nginx serves static files but they must be manually built

### Solution: Multi-Stage Frontend Build

**Create File**: `frontend/Dockerfile`

```dockerfile
# ============================================
# Multi-stage build for React + Vite frontend
# ============================================

# Stage 1: Builder
FROM node:20-alpine as builder

WORKDIR /app

# Copy package files
COPY package*.json ./
COPY yarn.lock* ./

# Install dependencies (with caching)
RUN npm ci --prefer-offline --no-audit || yarn install --frozen-lockfile

# Copy source code
COPY . .

# Build Vite app
RUN npm run build

# ============================================
# Stage 2: Runtime - Nginx
FROM nginx:alpine

# Copy built assets from builder
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Expose port
EXPOSE 3000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD wget -q -O - http://localhost:3000 > /dev/null || exit 1

# Start nginx
CMD ["nginx", "-g", "daemon off;"]
```

---

## 🎯 Fix #3: Update docker-compose.yml for Frontend Build

### Current Setup
Nginx uses pre-built `./frontend/dist` but doesn't build it.

### Updated Setup with Frontend Service

**Replace nginx service** in `docker-compose.yml`:

```yaml
  # Frontend UI with automatic build
  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    container_name: pilotforge-ui
    restart: unless-stopped
    ports:
      - "3000:3000"
    depends_on:
      - backend
    environment:
      - VITE_API_URL=http://localhost:8000
    healthcheck:
      test: ["CMD", "wget", "-q", "-O", "-", "http://localhost:3000"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 10s
    networks:
      - tax-incentive-network
    profiles:
      - dev  # Only build in development

  # Optional: Keep nginx for static serving in production
  nginx:
    image: nginx:alpine
    container_name: pilotforge-nginx
    restart: unless-stopped
    ports:
      - "80:80"
    volumes:
      - ./nginx.conf:/etc/nginx/conf.d/default.conf:ro
      - ./frontend/dist:/usr/share/nginx/html:ro
    depends_on:
      - backend
    networks:
      - tax-incentive-network
    profiles:
      - prod  # Only use in production
```

### Usage

**Development** (with live frontend build):
```bash
docker compose up --profile dev
```

**Production** (pre-built frontend):
```bash
npm run build --prefix frontend
docker compose up --profile prod
```

---

## 🎯 Fix #4: Create/Update nginx.conf

**Create/Verify**: `nginx.conf`

```nginx
# Frontend Nginx Configuration
upstream backend {
    server backend:8000;
}

server {
    listen 80;
    listen 3000;
    server_name _;

    # Serve React/Vite static files
    root /usr/share/nginx/html;
    index index.html;

    # SPA routing: send all non-asset requests to index.html
    location / {
        try_files $uri $uri/ /index.html;
    }

    # Static assets - cache aggressively
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
        expires 365d;
        add_header Cache-Control "public, immutable";
        access_log off;
    }

    # API proxy to FastAPI backend
    location /api {
        proxy_pass http://backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 60s;
    }

    # Health check endpoint for Docker
    location /health {
        return 200 "OK";
        add_header Content-Type text/plain;
    }

    # Deny access to sensitive files
    location ~ /\. {
        deny all;
        access_log off;
        log_not_found off;
    }
}
```

---

## 🎯 Fix #5: Frontend Environment Setup

### Create File: `frontend/.env.example`

```env
# API Configuration
VITE_API_URL=http://localhost:8000
VITE_API_TIMEOUT=30000

# Feature Flags
VITE_ENABLE_ANALYTICS=true
VITE_ENABLE_SENTRY=false

# App Configuration
VITE_APP_NAME=SceneIQ
VITE_APP_VERSION=0.0.1
```

### Create File: `frontend/.dockerignore`

```
node_modules
npm-debug.log
dist
.git
.gitignore
.env.local
.DS_Store
coverage
.vscode
.idea
*.swp
```

---

## 🎯 Fix #6: Optimize Backend Image Size

### Current: 3.53GB → Target: ~800MB

**Update**: `Dockerfile` (Backend)

```dockerfile
# Stage 1: Builder (unchanged)
FROM python:3.12-slim as builder

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

# Stage 2: Runtime (OPTIMIZED)
FROM python:3.12-slim

WORKDIR /app

# Install minimal runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql-client \
    libatomic1 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && rm -rf /tmp/* /var/tmp/*

# Copy Python packages from builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy Prisma binaries - optimize by excluding unnecessary files
COPY --from=builder /root/.cache /root/.cache

# Copy only necessary application code
COPY src ./src
COPY prisma ./prisma
COPY main.py pyproject.toml ./

# Remove Python cache files
RUN find . -type d -name '__pycache__' -exec rm -rf {} + 2>/dev/null || true && \
    find . -type f -name '*.pyc' -delete

# Set Prisma environment variables
ENV PRISMA_PYTHON_BINARY_CACHE_DIR=/root/.cache/prisma-python
ENV XDG_CACHE_HOME=/root/.cache
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health', timeout=5)"

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Optimization Tips**:
- Review `requirements.txt` for bloat (numpy, pandas, etc. add 500MB+)
- Use `pip --no-cache-dir` (already done)
- Combine RUN commands to reduce layers
- Remove unnecessary development dependencies
- Use distroless base if possible

---

## 🎯 Fix #7: Clean Up Legacy Images

```bash
# Remove unused images
docker image rm aura-backend:latest aura-frontend:test aura-backend:test
docker image rm script_parser_project-backend:latest script_parser_project-frontend:latest
docker image rm mcp/playwright

# Prune dangling images
docker image prune -a --force

# Check space freed
docker system df
```

---

## 🎯 Fix #8: Update docker-compose.prod.yml

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:16-alpine
    container_name: pilotforge-db-prod
    restart: always
    environment:
      POSTGRES_USER: ${DB_USER:-postgres}
      POSTGRES_PASSWORD: ${DB_PASSWORD}
      POSTGRES_DB: tax_incentive_db
      POSTGRES_INITDB_ARGS: "-c shared_buffers=256MB -c max_connections=200"
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    networks:
      - tax-incentive-network
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${DB_USER:-postgres}"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 40s
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

  backend:
    build:
      context: .
      dockerfile: Dockerfile
    image: ${DOCKER_REGISTRY}/pilotforge:${APP_VERSION:-latest}
    container_name: pilotforge-api-prod
    restart: always
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://${DB_USER:-postgres}:${DB_PASSWORD}@postgres:5432/tax_incentive_db
      - APP_ENV=production
      - LOG_LEVEL=INFO
      - ALLOWED_ORIGINS=${ALLOWED_ORIGINS:-https://app.example.com}
      - PYTHONUNBUFFERED=1
    depends_on:
      postgres:
        condition: service_healthy
    networks:
      - tax-incentive-network
    healthcheck:
      test: ["CMD", "python", "-c", "import requests; requests.get('http://localhost:8000/health', timeout=5)"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 512M
        reservations:
          cpus: '0.5'
          memory: 256M

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    image: ${DOCKER_REGISTRY}/pilotforge-ui:${APP_VERSION:-latest}
    container_name: pilotforge-ui-prod
    restart: always
    ports:
      - "3000:3000"
    depends_on:
      - backend
    networks:
      - tax-incentive-network
    healthcheck:
      test: ["CMD", "wget", "-q", "-O", "-", "http://localhost:3000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 10s
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

  redis:
    image: redis:7-alpine
    container_name: pilotforge-cache-prod
    restart: always
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    networks:
      - tax-incentive-network
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

volumes:
  postgres_data:
    driver: local
  redis_data:
    driver: local

networks:
  tax-incentive-network:
    driver: bridge
```

---

## 📋 Implementation Checklist

### Immediate (Now)
- [ ] Fix #1: Update desksos-enterprise-client health check (install curl or use wget)
- [ ] Fix #5: Create frontend/.dockerignore
- [ ] Fix #5: Create frontend/.env.example

### Short-term (This week)
- [ ] Fix #2: Create frontend/Dockerfile with multi-stage build
- [ ] Fix #3: Update docker-compose.yml to include frontend build service
- [ ] Fix #4: Create/update nginx.conf with proper configuration
- [ ] Test: `docker compose up` with frontend build

### Medium-term (This sprint)
- [ ] Fix #6: Optimize backend Dockerfile (reduce image size)
- [ ] Fix #7: Clean up legacy images
- [ ] Fix #8: Update docker-compose.prod.yml with new frontend service
- [ ] Test: Production deployment with both compose files

### Long-term (Next iteration)
- [ ] Set up CI/CD to build and push images
- [ ] Add Kubernetes deployment manifests
- [ ] Implement monitoring and alerting for health checks
- [ ] Performance testing and optimization

---

## ✅ Verification Commands

```bash
# Build frontend
cd frontend && npm run build

# Test development stack
docker compose up --profile dev

# Verify health checks
docker ps --format "table {{.Names}}\t{{.Status}}"

# View logs
docker logs pilotforge-api
docker logs pilotforge-ui

# Test API health endpoint
curl http://localhost:8000/health

# Test frontend
curl http://localhost:3000/health

# Check image sizes
docker images --format "table {{.Repository}}:{{.Tag}}\t{{.Size}}"

# Inspect health history
docker inspect pilotforge-ui | grep -A 10 '"Health"'
```

