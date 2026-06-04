# Security Overview

This document summarizes required security work and actionable controls for:
- RBAC implementation
- Audit logging
- Authentication improvements
- AI failover behavior
- Monitoring integrations
- Backup scripts
- Permission checks

Keep each change small and review in a PR with an approver from Security.
## RBAC implementation

- Define canonical roles (e.g., `admin`, `power-user`, `operator`, `auditor`, `service`) and map them to least-privilege permissions.
- Store role/permission mappings centrally (database or config repo). Use `create_admin.py` and `seed_pse_assignments.py` as integration points for seeding roles.
- Enforce role checks in every service boundary and middleware. Prefer attribute-based checks where fine-grained control is needed.
- Add an approval workflow for role elevation; record all grant/revoke events in the audit log.

## Audit logging
- Emit structured, tamper-evident logs (JSON) for authentication, authorization, role changes, backup/restore, and AI-driven decisions.
- Forward logs to a central system (ELK / Splunk / CloudWatch / Datadog). Retain immutable copies for compliance windows.
- Include correlation IDs in requests to trace cross-service flows.
- Define log retention and access policies; restrict who can export or delete audit logs.

## Authentication improvements
- Require multi-factor authentication (MFA) for all interactive accounts and admin/API key rotations for service accounts.
- Integrate SSO/OIDC where available; use short-lived tokens and refresh tokens with revocation support.
- Enforce strong password rules and replay protection; set session idle and absolute timeouts.
- Centralize credential storage (secret manager / Key Vault) and rotate secrets automatically with alerts on failures.

## AI failover behavior
- Default AI-driven automations to a conservative fail-closed mode: when uncertain or on error, the system should not perform side-effecting actions.
- Implement a circuit breaker for AI subsystems; on repeated failures or degraded confidence, route decisions to a human review queue.
- Log AI inputs, model decisions, confidence scores, and final actions for audit and post-mortem.
- Provide an emergency override only to authorized roles and record overrides in audit logs.

## Monitoring integrations
- Export health, latency, error rates, and key business metrics to Prometheus (instrumentation) and visualize in Grafana.
- Integrate existing `monitor.py` and `health-check.ps1` into the monitoring checks and synthetic tests.
- Create alert rules for authentication failures, permission errors, audit-log gaps, backup failures, and AI circuit-breaker trips.
- Define alert runbooks and on-call escalation for critical alerts.

## Backup scripts
- Provide scheduled backups for critical data stores and configuration. Use existing `restore.ps1` as the restore path; add `backup.ps1` that:
        - Takes consistent snapshots (DB + object store metadata)
        - Verifies checksums after upload
        - Rotates backups and enforces retention policy

Example minimal `backup.ps1` pattern (place in `scripts/backup.ps1`):

```powershell
# Example: create DB dump, compress, upload to blob storage
param([string]$OutDir = "./backups")
New-Item -ItemType Directory -Path $OutDir -Force | Out-Null
# TODO: replace with real DB dump commands
Write-Output "Dumping DB to $OutDir/db.sql"
# Compress and upload steps here
Write-Output "Upload complete"
```

## Permission checks
- Implement automated permission-check tests that assert least-privilege for each role and service account.
- Add a CI gate that runs permission matrix tests on PRs which change access control code or role mappings.
- Periodically (quarterly) run an access review: list principals with elevated rights and validate necessity.

## Next steps
- Implement RBAC mapping and seed roles (`Design RBAC model and mapping`).
- Add structured audit logging and configure a log sink (`Specify audit logging requirements`).
- Create `scripts/backup.ps1` and schedule it; wire restore tests to `restore.ps1`.
- Add CI tests for permission checks and enable alerting for audit-log gaps.

If you want, I can open PRs to add `scripts/backup.ps1`, CI permission tests, and the RBAC seeders next. 
# Security Overview — SceneIQ Platform

**Document:** docs/security/security-overview.md  
**Classification:** Internal  
**Last Updated:** 2026-05-31

---

## 1. Authentication Model

### How Users Authenticate

SceneIQ uses **JWT (JSON Web Token)** based authentication served through the FastAPI backend.

```
User submits credentials (email + password)
        ↓
FastAPI /auth/login endpoint
        ↓
Password verified against bcrypt hash in PostgreSQL
        ↓
JWT access token issued (signed with SECRET_KEY)
        ↓
Token stored client-side (httpOnly cookie or Authorization header)
        ↓
All subsequent API requests include Bearer token
        ↓
FastAPI middleware validates token on every protected route
```

### Password Requirements

| Requirement        | Current Standard         | Recommended Enterprise Standard |
|--------------------|--------------------------|----------------------------------|
| Minimum length     | 8 characters             | 12 characters                    |
| Complexity         | Not enforced             | ⚠️ Must enforce: upper, lower, number, symbol |
| Hashing algorithm  | bcrypt                   | bcrypt (acceptable, keep)        |
| Breach checking    | Not implemented          | ⚠️ Recommend: HaveIBeenPwned API |
| Failed login limit | Not implemented          | ⚠️ Recommend: 5 attempts, 15-min lockout |

> **ACTION REQUIRED:** Password complexity and brute-force lockout are not currently enforced. These must be implemented before enterprise deployment.

### JWT Lifecycle

| Property         | Current Value         | Notes                              |
|------------------|-----------------------|------------------------------------|
| Algorithm        | HS256                 | Acceptable for current scale       |
| Access token TTL | Recommend: 60 minutes | Verify in `auth.py` / `.env`       |
| Refresh token    | Not confirmed         | ⚠️ Discovery task — verify implementation |
| Token revocation | Not implemented       | ⚠️ Required for enterprise logout  |
| Secret key       | Environment variable  | ✅ Correct — never hardcode         |

**JWT Secret Key Management:**
```
# Correct pattern (Railway environment variable)
SECRET_KEY=<generated-256-bit-secret>

# Never do this
SECRET_KEY="mysecretkey123"  # hardcoded = critical vulnerability
```

**Generating a secure secret key:**
```bash
# Run this in PowerShell or bash to generate a proper secret
python -c "import secrets; print(secrets.token_hex(32))"
```

---

## 2. Authorization Model

### Role-Based Access Control (RBAC)

SceneIQ uses role-based authorization. Full RBAC design is documented in Phase 3. Summary of roles:

| Role               | Access Level                              |
|--------------------|-------------------------------------------|
| Administrator      | Full system control                       |
| Compliance Manager | Rule approval, incentive oversight        |
| Producer           | Production management                     |
| Coordinator        | Data entry, workflow support              |
| Read-Only          | View access only                          |

### Route Protection Pattern

All API routes requiring authentication must use FastAPI dependency injection:

```python
# Correct pattern — every protected route must include this
from app.auth import get_current_user

@router.get("/productions")
async def get_productions(current_user: User = Depends(get_current_user)):
    ...

# Incorrect — unprotected route (creates unauthorized access risk)
@router.get("/productions")
async def get_productions():
    ...
```

### Known Authorization Gaps (Discovery Tasks)

- [ ] Audit every router file to confirm `Depends(get_current_user)` is present on all non-public routes
- [ ] Confirm admin-only routes check for `role == "administrator"` — not just authentication
- [ ] Confirm that Stripe webhook endpoints validate Stripe signatures (not just open POST endpoints)
- [ ] Confirm CORS `allow_origins` is not set to `["*"]` in production

---

## 3. Secret Management

### Current Secret Inventory

| Secret                  | Storage Location          | Status     |
|-------------------------|---------------------------|------------|
| DATABASE_URL            | Railway environment vars  | ✅ Correct  |
| ANTHROPIC_API_KEY       | Railway environment vars  | ✅ Correct  |
| STRIPE_SECRET_KEY       | Railway environment vars  | ✅ Correct  |
| STRIPE_WEBHOOK_SECRET   | Railway environment vars  | ✅ Correct  |
| SECRET_KEY (JWT)        | Railway environment vars  | ✅ Correct  |
| Web3Forms access key    | Embedded in HTML          | ⚠️ Review — public-facing but low-risk |
| BREVO API key           | Verify location           | 🔍 Discovery task |

### Environment Variable Handling Rules

```python
# Correct: load from environment, fail loudly if missing
import os
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL environment variable is not set")

# Wrong: fallback to a hardcoded value
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://localhost/sceneiq")
```

### .gitignore Verification Checklist

Confirm these are in `.gitignore` before every push:

```
.env
.env.local
.env.production
*.pem
*.key
__pycache__/
node_modules/
prisma/.env
```

---

## 4. API Security

### CORS Configuration

```python
# Correct production CORS — whitelist only your domains
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://getsceneiq.com",
        "https://aura.getsceneiq.com",
        "https://contractreview.getsceneiq.com",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)

# Wrong — never use in production
allow_origins=["*"]
```

### Rate Limiting

The Anthropic API rate limiter with exponential backoff is already implemented. Extend this pattern to:

- [ ] `/auth/login` — prevent brute force
- [ ] `/auth/register` — prevent account farming
- [ ] All AI Advisor endpoints — already done, verify still active

### Input Validation

FastAPI + Pydantic provides automatic input validation. Ensure:

- [ ] All request bodies use Pydantic models (no raw `dict` parsing)
- [ ] File upload endpoints (if any) validate file type and size
- [ ] No `eval()` or `exec()` used anywhere in the codebase

---

## 5. Database Security

### Connection Security

```
# Railway internal URL (preferred — stays within Railway private network)
DATABASE_URL=postgresql://user:pass@postgres.railway.internal:5432/railway

# Railway external proxy URL (use only for local development/seeding)
DATABASE_URL=postgresql://user:pass@roundhouse.proxy.rlwy.net:PORT/railway
```

- Never commit the external proxy URL to version control
- Internal URL is not reachable from the public internet — always prefer it for production

### Prisma ORM Protection

Prisma parameterizes all queries by default, which prevents SQL injection. Rules:

- [ ] Never use `$queryRaw` with string interpolation — use `$queryRaw` with tagged template literals only
- [ ] Never disable Prisma query logging in production without replacing it with your own audit log

---

## 6. Security Audit Checklist — Phase 1 Findings

Run this checklist against the repository before enterprise launch:

### Critical (Must Fix Before Launch)
- [ ] Password complexity requirements enforced
- [ ] Failed login lockout implemented (5 attempts / 15 min)
- [ ] JWT token revocation on logout (blacklist or short TTL + refresh token rotation)
- [ ] CORS not set to `["*"]` in production
- [ ] All admin routes verify role, not just authentication
- [ ] Stripe webhook signature validation confirmed

### High (Fix Within 30 Days)
- [ ] Rate limiting on `/auth/login` and `/auth/register`
- [ ] Brevo API key location confirmed and secured
- [ ] Refresh token flow documented and tested
- [ ] All environment variables fail loudly if missing (no silent fallbacks)

### Medium (Fix Within 90 Days)
- [ ] HaveIBeenPwned API integration for breach checking
- [ ] Security headers added (Content-Security-Policy, X-Frame-Options, HSTS)
- [ ] Dependency vulnerability scanning (pip-audit, npm audit) added to deployment checklist
- [ ] Session activity timeout for idle users

### Low (Track as Technical Debt)
- [ ] Web3Forms key review (public-facing, assess exposure risk)
- [ ] API versioning strategy documented (`/api/v1/`)
- [ ] Penetration test scheduled for post-launch

---

*Related documents: [Data Retention](data-retention.md) | [Incident Response](incident-response.md)*
