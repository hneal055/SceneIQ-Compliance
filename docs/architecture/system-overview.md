# SceneIQ System Overview

## Purpose

SceneIQ is a Film & Television Tax Incentive Intelligence Platform that assists production companies, compliance teams, producers, and financial stakeholders in evaluating, managing, and qualifying for film and television tax incentive programs across multiple jurisdictions.

The platform combines incentive intelligence, production operations, scheduling, compliance tracking, AI-assisted guidance, and jurisdiction analysis into a unified workflow.

---

## Core Business Functions

### Incentive Intelligence

- Jurisdiction discovery
- Incentive qualification analysis
- Credit estimation
- Incentive stacking evaluation

### Production Management

- Production tracking
- Jurisdiction assignment
- Spend monitoring
- Compliance workflows

### Scheduling Intelligence

- Script breakdown imports
- Stripboard generation
- Day Out of Days generation
- Jurisdiction shoot-day tracking

### Compliance Operations

- Rule management
- Rule approval workflows
- Local incentive tracking
- Qualification monitoring

### AI Assistance

- Qualification guidance
- Incentive research
- Jurisdiction comparison support

---

## High-Level Architecture

Frontend Layer
→ React / TypeScript / Vite

Backend Layer
→ FastAPI / Python

Persistence Layer
→ PostgreSQL / Prisma

AI Layer
→ Anthropic Claude

Infrastructure Layer
→ Docker
→ Nginx
→ Railway

---

## Major Platform Modules

### Dashboard

Provides executive visibility into:

- Active productions
- Estimated credits
- Spend tracking
- Incentive opportunities

### Productions

Manages production records, jurisdictions, qualification requirements, and incentive participation.

### Jurisdictions

Stores state, county, city, and international incentive programs.

### Incentive Calculator

Calculates estimated credits and incentive qualification metrics.

### Scenario Calculator

Compares multiple jurisdictions and evaluates stacking opportunities.

### Production Schedule Engine

Tracks:

- Script breakdowns
- Stripboards
- Day Out of Days reports
- Call sheets
- Jurisdiction shoot-day counts

### Transmission Log

Tracks broadcast activity and post-production distribution schedules.

### Rule Review

Provides approval workflow for AI-assisted incentive rule extraction.

### Administration

Provides user and platform management capabilities.

---

## Architectural Objectives

- Maintain deterministic incentive calculations.
- Preserve auditability of compliance workflows.
- Support future multi-tenant SaaS deployment.
- Enable enterprise governance controls.
- Separate AI advisory functions from calculation engines.
- Support secure and scalable cloud deployment.

---

## Future Documentation

Additional architecture documentation:

- frontend.md
- backend.md
- database.md
- integrations.md
- deployment.md

These documents will provide deeper technical details regarding system design and operational architecture.
