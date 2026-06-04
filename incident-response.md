# Incident Response Plan — SceneIQ Platform

**Document:** docs/security/incident-response.md  
**Classification:** Internal — Restricted  
**Last Updated:** 2026-05-31

---

## Overview

This document defines how Scene Reader Studio Technologies LLC responds to security incidents affecting the SceneIQ platform. It establishes classification levels, response procedures, communication templates, and post-incident requirements.

---

## 1. Incident Classification

### Severity Levels

| Severity | Name       | Description                                                                 | Response Time |
|----------|------------|-----------------------------------------------------------------------------|---------------|
| SEV-1    | Critical   | Active breach, data exfiltration, full service compromise                   | Immediate     |
| SEV-2    | High       | Suspected breach, unauthorized access, significant data exposure            | Within 2 hours|
| SEV-3    | Medium     | Failed attack attempts, suspicious activity, partial service degradation    | Within 24 hours|
| SEV-4    | Low        | Vulnerability discovered (no active exploitation), minor anomaly            | Within 72 hours|

---

## 2. Incident Response Roles

| Role                    | Responsible Party              | Contact                        |
|-------------------------|--------------------------------|--------------------------------|
| Incident Commander      | Howard Neal (Founder/CEO)      | Primary decision authority     |
| Technical Lead          | Howard Neal                    | Investigation and remediation  |
| Customer Communications | Howard Neal                    | User and stakeholder notices   |
| Legal/Compliance        | External counsel (as needed)   | Breach notification law        |

> **NOTE:** At current company size, Howard Neal holds all incident response roles. As the team grows, these must be formally distributed.

---

## 3. Incident Response Phases

### Phase 1 — Detection

Incidents may be detected via:
- Railway service alerts or anomaly notifications
- Cloudflare security event alerts
- User reports via support@getsceneiq.com
- Stripe fraud or dispute notifications
- Anthropic API usage anomalies (unexpected token spikes)
- Manual observation during operations

**Detection Checklist:**
- [ ] Document the time of detection
- [ ] Document the detection source (alert, user report, manual)
- [ ] Assign initial severity classification
- [ ] Open an incident record (private GitHub issue or secure document)

---

### Phase 2 — Containment

**For SEV-1 / SEV-2 (Active or Suspected Breach):**

```
IMMEDIATE ACTIONS (do these first, in order):

1. Rotate all secrets immediately:
   - Railway: regenerate DATABASE_URL, SECRET_KEY, ANTHROPIC_API_KEY, STRIPE_SECRET_KEY
   - Cloudflare: review access logs, rotate API token if affected
   - Stripe: rotate secret key in Stripe dashboard

2. Revoke all active JWT tokens:
   - If token blacklist exists: flush it
   - If not: change SECRET_KEY (this invalidates all existing tokens)

3. Assess service continuity:
   - Can the platform operate safely? If not → take service offline
   - Railway: remove the service's custom domain or set a maintenance page

4. Preserve evidence:
   - Export Railway logs before rotating secrets
   - Screenshot any anomalous activity
   - Do NOT delete logs during investigation
```

**For SEV-3 / SEV-4 (Suspicious Activity / Vulnerability):**
- Document the finding in detail
- Do not rotate secrets preemptively unless active exploitation is confirmed
- Assess scope before taking action
- Assign remediation task with target resolution date

---

### Phase 3 — Investigation

**Questions to answer during investigation:**

1. What was accessed?
   - PostgreSQL: query `audit_logs` table for affected records
   - Railway: review deployment and access logs
   - Stripe: review Stripe dashboard for unauthorized API calls

2. Who was affected?
   - Which user accounts were involved?
   - Which production records were potentially exposed?
   - Were payment references accessed?

3. How did it happen?
   - Authentication failure (brute force, credential theft)?
   - Authorization bypass (missing role check on a route)?
   - Dependency vulnerability (check `pip-audit`, `npm audit`)?
   - Misconfiguration (CORS, exposed endpoint)?

4. How long did it last?
   - First anomalous event timestamp
   - Last anomalous event timestamp

**Investigation Log Template:**
```
Incident ID: INC-[DATE]-[SEQ]
Date/Time Detected: 
Date/Time Contained:
Severity: SEV-[1/2/3/4]
Summary:
Affected Systems:
Affected Users:
Root Cause:
Evidence Collected:
Actions Taken:
```

---

### Phase 4 — Notification

#### Internal Notification
- Document incident in private incident log immediately upon detection

#### Customer Notification (if user data affected)

**Trigger:** Any confirmed unauthorized access to user account data, production data, or payment references.

**Timing:** Notify within 72 hours of confirmed breach (GDPR requirement; best practice regardless of jurisdiction).

**Customer Notification Template:**
```
Subject: Important Security Notice from SceneIQ

Dear [Name],

We are writing to notify you of a security incident that may have affected your SceneIQ account.

What happened:
[Plain-language description — be specific without revealing exploitation details]

What information was involved:
[List exactly what data was potentially accessed]

What we have done:
[Concrete actions taken: secrets rotated, accounts secured, etc.]

What you should do:
- Change your SceneIQ password immediately
- If you use the same password elsewhere, change it there as well
- Review your account for any unauthorized changes
- Contact us at support@getsceneiq.com if you notice anything unusual

We take the security of your data seriously. We apologize for this incident and are committed to preventing future occurrences.

Howard Neal
Founder & CEO, Scene Reader Studio Technologies LLC
```

#### Regulatory Notification

| Regulation | Trigger                        | Deadline       | Contact              |
|------------|--------------------------------|----------------|----------------------|
| CCPA       | CA resident data affected      | Expedient      | California AG        |
| GDPR       | EU resident data affected      | 72 hours       | Relevant DPA         |
| State laws | Varies by state                | Varies         | Consult legal counsel|

> **IMPORTANT:** Do not make regulatory notification decisions without legal counsel. Premature or incorrect notifications can create additional liability.

---

### Phase 5 — Recovery

```
Recovery Checklist:

[ ] Root cause confirmed and documented
[ ] Vulnerability patched or mitigated
[ ] All secrets rotated (if applicable)
[ ] All affected user accounts notified
[ ] Service restored and validated (run smoke tests)
[ ] Railway logs reviewed to confirm no ongoing anomalous activity
[ ] Stripe account reviewed — no unauthorized charges
[ ] Anthropic API usage reviewed — no unexpected consumption
[ ] Customer-facing status update posted (if service was degraded)
```

---

### Phase 6 — Post-Incident Review

Within 5 business days of resolution, complete a post-incident review document:

```
POST-INCIDENT REVIEW

Incident ID:
Resolution Date:
Total Duration (detection to resolution):

Timeline:
- [Timestamp] — [Event]

Root Cause:

What worked well:

What did not work:

Action items to prevent recurrence:
| Action | Owner | Target Date |

Was this incident preventable?

Customer impact summary:
```

---

## 4. Quick Reference — Key Actions by Scenario

| Scenario                          | First Action                          |
|-----------------------------------|---------------------------------------|
| Suspected credential theft        | Rotate SECRET_KEY → invalidates all JWTs |
| Database connection string exposed| Rotate DATABASE_URL in Railway immediately |
| Anthropic API key exposed         | Rotate key in Anthropic console       |
| Stripe key exposed                | Rotate in Stripe dashboard, check logs for unauthorized calls |
| Railway account compromised       | Reset Railway account password, review all environment variables |
| Cloudflare account compromised    | Reset password, check DNS records for unauthorized changes |

---

## 5. Contact Directory

| Service    | Security/Support URL                              |
|------------|---------------------------------------------------|
| Railway    | https://railway.app/help                          |
| Cloudflare | https://dash.cloudflare.com → Support             |
| Stripe     | https://support.stripe.com                        |
| Anthropic  | https://support.anthropic.com                     |
| Brevo      | https://help.brevo.com                            |

---

*Related documents: [Security Overview](security-overview.md) | [Data Retention](data-retention.md)*
