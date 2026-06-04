# Integrations Architecture

## Overview

SceneIQ integrates with external systems to support incentive intelligence, production operations, scheduling workflows, and AI-assisted guidance.

---

## AI Integration

### Anthropic Claude

Purpose:

* Qualification guidance
* Incentive research assistance
* Jurisdiction comparisons
* Advisory recommendations

Architecture principle:

AI may provide guidance but must not directly determine incentive eligibility or financial calculations.

---

## Production Scheduling Integrations

### Movie Magic Scheduling

Supported import:

```text
.mms
```

Purpose:

* Production scheduling import
* Stripboard generation
* Shoot-day tracking

---

### Final Draft

Supported import:

```text
.fdx
```

Purpose:

* Script breakdown ingestion
* Production planning workflows

---

### CSV Imports

Supported sources:

* Movie Magic Budgeting
* Showbiz Budgeting
* Scenechronize
* Spreadsheet exports

Purpose:

* Budget imports
* Production data imports
* Scheduling workflows

---

## Broadcast Operations

### Transmission Log Imports

Supported formats:

* CSV
* XML
* JSON
* BXF

Purpose:

* Broadcast activity tracking
* Distribution compliance
* Airing verification

---

## Data Intelligence Integrations

### Feed Monitoring

Purpose:

* Jurisdiction monitoring
* Incentive updates
* Rule extraction workflows

Outputs:

* Pending Rules
* Local Rules
* Compliance Requirements

---

## Authentication

Current authentication model:

* JWT Bearer Tokens

Future considerations:

* SSO
* SAML
* OAuth providers
* Enterprise identity federation

---

## Infrastructure Integrations

### Railway

Purpose:

* Application hosting
* Deployment automation

### Docker Hub

Purpose:

* Container image storage

---

## Architectural Principles

### Human Oversight

AI-generated content requires review before becoming authoritative platform data.

### Deterministic Calculations

Calculation engines remain independent from AI-generated recommendations.

### Auditability

External data sources should be traceable to original sources.

### Security

External integrations must use environment-based credential management.

---

## Future Integration Opportunities

* EP Payroll systems
* Entertainment Partners
* Cast & Crew
* Studio ERP platforms
* Production accounting software
* Government incentive feeds
* Identity providers
* Analytics platforms
