# Data Retention Policy — SceneIQ Platform

**Document:** docs/security/data-retention.md  
**Classification:** Internal / Customer-Facing  
**Last Updated:** 2026-05-31

---

## Overview

This document defines how SceneIQ collects, stores, retains, and deletes user and production data. This policy applies to all data processed by the SceneIQ Tax Incentive Intelligence Platform, SceneIQ Budget Builder, and AURA Enterprise.

---

## 1. Data We Collect

### User Account Data
| Data Type              | Purpose                         | Storage Location  |
|------------------------|---------------------------------|-------------------|
| Email address          | Authentication, notifications   | PostgreSQL        |
| Password (hashed)      | Authentication                  | PostgreSQL        |
| Name                   | Account identification          | PostgreSQL        |
| Role assignment        | Authorization                   | PostgreSQL        |
| Account creation date  | Audit trail                     | PostgreSQL        |
| Last login timestamp   | Security monitoring             | PostgreSQL        |

### Production Data
| Data Type                    | Purpose                          | Storage Location  |
|------------------------------|----------------------------------|-------------------|
| Production name and details  | Core platform function           | PostgreSQL        |
| Jurisdiction selections      | Tax incentive calculation        | PostgreSQL        |
| Budget figures               | Incentive optimization           | PostgreSQL        |
| Schedule data                | Production management            | PostgreSQL        |
| Uploaded schedules (CSV/FDX) | Import processing                | Transient only    |
| Compliance tracking records  | Audit trail                      | PostgreSQL        |

### AI Advisor Interaction Data
| Data Type                  | Purpose                        | Storage Location        |
|----------------------------|--------------------------------|-------------------------|
| User queries to AI Advisor | Platform functionality         | Not persisted — transient |
| AI Advisor responses       | Platform functionality         | Not persisted — transient |
| Transmission log entries   | Audit trail (user-visible)     | PostgreSQL              |

> **Important:** SceneIQ does not train AI models on user queries. Queries sent to the Anthropic API are subject to [Anthropic's data usage policy](https://www.anthropic.com/legal/privacy).

### Payment Data
| Data Type              | Purpose              | Storage Location             |
|------------------------|----------------------|------------------------------|
| Stripe customer ID     | Subscription mgmt    | PostgreSQL (reference only)  |
| Subscription status    | Access control       | PostgreSQL                   |
| Payment card details   | Billing              | Stripe only — never SceneIQ  |

---

## 2. Retention Periods

| Data Category                | Retention Period          | Deletion Trigger              |
|------------------------------|---------------------------|-------------------------------|
| Active user accounts         | Duration of subscription  | Account cancellation + 90 days|
| Production records           | Duration of subscription  | Account deletion request      |
| Compliance audit logs        | 7 years                   | Regulatory requirement        |
| Authentication logs          | 90 days                   | Rolling — auto-purge          |
| Failed login logs            | 30 days                   | Rolling — auto-purge          |
| AI Advisor transmission logs | 1 year                    | Annual purge or user request  |
| Stripe payment references    | 7 years                   | Tax/legal requirement         |
| Uploaded file data (transient)| Session only             | Purged after import processing|

---

## 3. Data Deletion

### User-Requested Deletion

Users may request deletion of their account and associated data by:
1. Emailing support@getsceneiq.com with subject: `[Data Deletion Request]`
2. Providing their registered email address
3. Receiving confirmation within 30 business days

**What gets deleted:**
- User account record
- All production records owned by the user
- AI Advisor transmission logs
- Associated compliance records (except those subject to 7-year retention)

**What is retained:**
- Aggregated, anonymized analytics (no PII)
- Compliance audit logs as required by law
- Stripe transaction records (Stripe-side, not SceneIQ-side)

### Automated Deletion

The following are purged automatically on a rolling schedule:

```
Authentication logs     → 90 days rolling
Failed login attempts   → 30 days rolling
Temporary upload files  → Immediately after processing
```

> **IMPLEMENTATION NOTE:** Automated purge jobs are not yet implemented. This is a Phase 4 (Audit Logging) deliverable. Add scheduled PostgreSQL cleanup jobs via Railway cron or a background task worker.

---

## 4. Data Residency

| Component          | Provider   | Region                  |
|--------------------|------------|-------------------------|
| PostgreSQL database| Railway    | US (verify exact region in Railway dashboard) |
| API backend        | Railway    | US                      |
| Frontend static    | GitHub Pages / Railway | US           |
| AI processing      | Anthropic  | US (Anthropic infrastructure) |
| Payment processing | Stripe     | US                      |
| Email delivery     | Brevo      | EU (verify — check Brevo account settings) |

> **NOTE:** If enterprise customers require data to remain exclusively in the US, verify Brevo data residency and consider a US-based alternative (SendGrid, AWS SES) for email delivery.

---

## 5. Data Access Controls

| Who Can Access Production Data | Conditions                              |
|--------------------------------|-----------------------------------------|
| The account owner              | Always                                  |
| Assigned team members          | If role grants access (Producer, Coordinator) |
| SceneIQ administrators         | For support purposes only — logged      |
| Third parties                  | Never — no data sharing or selling      |

---

## 6. Compliance Considerations

This policy is designed to support compliance with:

- **CCPA** (California Consumer Privacy Act) — right to deletion, right to know
- **GDPR** (if EU customers onboard) — requires Data Processing Agreement (DPA)
- **SOC 2 Type II** (future) — audit log retention, access controls

> **DISCOVERY TASK:** If any enterprise customer is EU-based, a GDPR Data Processing Agreement (DPA) must be executed before onboarding. Consult legal counsel.

---

*Related documents: [Security Overview](security-overview.md) | [Incident Response](incident-response.md)*
