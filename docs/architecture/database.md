# Database Architecture

## Overview

SceneIQ uses PostgreSQL as its primary persistence layer with Prisma ORM for schema management and database access.

The database supports incentive intelligence, production management, compliance workflows, scheduling operations, AI-assisted rule extraction, and jurisdiction analysis.

---

## Technology Stack

| Component           | Technology                 |
| ------------------- | -------------------------- |
| Database            | PostgreSQL 16              |
| ORM                 | Prisma ORM (Python Client) |
| Migration System    | Prisma Migrations          |
| Identifier Strategy | UUID Primary Keys          |

---

## Core Domain Areas

### Jurisdictions

Primary jurisdiction registry.

Supports:

* States
* Counties
* Cities
* International jurisdictions

Key capabilities:

* Parent-child hierarchy
* Rule inheritance
* Jurisdiction relationships
* Feed monitoring

Primary model:

```text
Jurisdiction
```

---

### Incentive Rules

Stores incentive calculations and qualification criteria.

Primary model:

```text
IncentiveRule
```

Capabilities:

* Spend thresholds
* Credit percentages
* Fixed incentives
* Qualification requirements
* Effective date tracking

---

### Local Rules

Stores county and city incentive programs.

Primary model:

```text
LocalRule
```

Capabilities:

* Additive incentive stacking
* Local qualification rules
* Supplemental credits

---

### Rule Governance

AI-assisted rule extraction workflow.

Primary model:

```text
PendingRule
```

Capabilities:

* AI extraction review
* Human approval workflow
* Confidence scoring
* Publication controls

---

### Compliance Requirements

Non-financial qualification requirements.

Primary model:

```text
JurisdictionRequirement
```

Examples:

* Permit requirements
* Insurance requirements
* Registration requirements
* Designation requirements

---

### Productions

Tracks productions participating in incentive programs.

Primary model:

```text
Production
```

Capabilities:

* Jurisdiction assignment
* Budget tracking
* Qualification management
* Compliance monitoring

---

### Expenses

Tracks qualifying and non-qualifying expenditures.

Primary model:

```text
Expense
```

Capabilities:

* Spend categorization
* Qualification validation
* Vendor tracking
* Audit support

---

### Users

Authentication and platform access.

Primary model:

```text
User
```

Capabilities:

* Authentication
* Role assignment
* Saved scenarios
* Notification preferences

---

## Scheduling Domain

Production Schedule Engine stores:

* Scenes
* Shoot Days
* Call Sheets
* Cast Members
* Jurisdiction Shoot Days

These records support incentive qualification calculations based on verified production activity.

---

## Architectural Strengths

### Hierarchical Jurisdictions

Supports state, county, city, and international structures.

### Rule Inheritance

Supports parent-child policy relationships.

### Governance Workflow

AI-assisted extraction with human review.

### Incentive Stacking

Supports additive local incentives.

### Compliance Tracking

Financial and non-financial qualification requirements.

---

## Improvement Opportunities

### Audit Logging

Add immutable audit history tables.

### Multi-Tenant Design

Introduce tenant ownership model.

### Data Retention Policies

Formalize archival strategy.

### Reporting Layer

Create materialized reporting views.

### Permission Model

Expand user authorization beyond role strings.

---

## Future Database Objectives

* Enterprise audit subsystem
* Multi-tenant SaaS architecture
* Jurisdiction version history
* Incentive rule versioning
* Compliance evidence storage
* Analytics warehouse integration
