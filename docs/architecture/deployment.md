# Deployment Architecture

## Overview

SceneIQ is deployed using a containerized architecture supporting both local development and cloud deployment.

The platform consists of:

* React Frontend
* FastAPI Backend
* PostgreSQL Database
* Nginx Reverse Proxy

---

## High-Level Deployment

```text
User
  ↓
Frontend (React/Vite)
  ↓
Nginx
  ↓
FastAPI Backend
  ↓
PostgreSQL
```

---

## Local Development Environment

Managed through Docker Compose.

Services:

### PostgreSQL

Container:

```text
sceneiq-db
```

Responsibilities:

* Persistent application data
* Incentive rules
* Productions
* Users
* Scheduling data

---

### Backend API

Container:

```text
sceneiq-api
```

Responsibilities:

* Authentication
* Business logic
* Incentive calculations
* Compliance processing
* AI integration

---

### Frontend

Container:

```text
sceneiq-ui
```

Responsibilities:

* User interface
* Dashboard
* Scheduling workflows
* Scenario analysis

---

### Reverse Proxy

Container:

```text
sceneiq-nginx
```

Responsibilities:

* Request routing
* Frontend/backend proxying
* Entry point management

---

## Production Environment

Hosted on Railway.

Deployment strategy:

* Dockerfile-based deployment
* Automatic deployment from main branch
* Managed PostgreSQL
* Environment-variable configuration

---

## Environment Variables

Critical variables:

* DATABASE_URL
* JWT_SECRET
* SECRET_KEY
* APP_ENV
* ANTHROPIC_API_KEY

These must never be committed to source control.

---

## Health Monitoring

Current health checks:

### Database

PostgreSQL readiness validation.

### Backend

FastAPI availability check.

### Frontend

Frontend health endpoint verification.

---

## Architectural Strengths

* Containerized architecture
* Portable deployment model
* Cloud-ready infrastructure
* Environment-based configuration
* Automated deployment support

---

## Improvement Opportunities

### Security

* Remove hardcoded development secrets
* Secret rotation strategy
* Environment separation

### Reliability

* Automated backups
* Disaster recovery plan
* Deployment rollback strategy

### Observability

* Structured logging
* Error monitoring
* Metrics collection
* Distributed tracing

### Scalability

* Horizontal backend scaling
* Read replica strategy
* CDN integration

---

## Future Objectives

* Production observability stack
* Infrastructure-as-Code
* Staging environment
* Automated security scanning
* Backup verification automation
* Enterprise deployment governance
