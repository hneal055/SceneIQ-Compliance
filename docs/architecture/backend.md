# Backend Architecture

## Overview

The SceneIQ backend is a FastAPI-based service layer responsible for authentication, incentive calculations, jurisdiction management, production workflows, compliance operations, scheduling functions, and AI integrations.

---

## Directory Structure

```text
backend/app
├── api/
├── core/
├── db/
├── models/
├── schemas/
├── services/
├── main.py
└── __init__.py
```

---

## Component Responsibilities

### API Layer (`api/`)

Responsibilities:

* HTTP endpoint definitions
* Request routing
* Input validation
* Response formatting
* Authentication enforcement

The API layer should remain thin and delegate business logic to services.

---

### Core Layer (`core/`)

Responsibilities:

* Application settings
* Security configuration
* Authentication
* Authorization
* Global utilities

No business-domain logic should exist here.

---

### Database Layer (`db/`)

Responsibilities:

* Database sessions
* Connection management
* Transaction handling
* Database initialization

---

### Models Layer (`models/`)

Responsibilities:

* Database entities
* ORM mappings
* Persistent domain structures

Examples:

* User
* Production
* Jurisdiction
* IncentiveRule
* Scenario
* Schedule

---

### Schemas Layer (`schemas/`)

Responsibilities:

* Request validation
* Response serialization
* API contracts

Implemented using Pydantic.

---

### Services Layer (`services/`)

Responsibilities:

* Incentive calculations
* Qualification logic
* Scenario analysis
* Rule processing
* AI orchestration
* Scheduling workflows

The services layer should contain all domain business logic.

---

## Architectural Principles

### Thin Controllers

API endpoints should delegate business operations to services.

### Service-Oriented Logic

Business rules should remain centralized inside services.

### Deterministic Compliance Calculations

Incentive qualification and calculation engines must remain independent of AI-generated outputs.

### Separation of Concerns

API → Services → Database

No direct database manipulation inside route handlers.

---

## Current Backend Assessment

### Strengths

* Clear FastAPI project structure
* Separation of API and business logic
* Dedicated schemas layer
* Dedicated services layer
* Dedicated database abstraction layer

### Improvement Opportunities

* Add architectural decision records (ADRs)
* Expand automated test coverage
* Add centralized audit logging
* Implement role-based access controls
* Add tenant isolation design
* Introduce service interfaces for major domains

---

## Future Improvements

* Event-driven workflow architecture
* Background task processing
* Observability and tracing
* Compliance audit subsystem
* Enterprise permission model
* Multi-tenant SaaS readiness
