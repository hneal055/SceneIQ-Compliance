# SECURITY.md — SceneIQ Platform Security Policy

**Platform:** SceneIQ Tax Incentive Intelligence Platform  
**Maintained by:** Scene Reader Studio Technologies LLC  
**Last Updated:** 2026-05-31  
**Classification:** Public

---

## Reporting a Vulnerability

If you discover a security vulnerability in the SceneIQ platform, **do not open a public GitHub issue.**

Report privately to:

- **Email:** security@getsceneiq.com
- **Subject line:** `[SECURITY] Brief description`
- **Expected response time:** 72 hours

Include in your report:
- Description of the vulnerability
- Steps to reproduce
- Potential impact assessment
- Your contact information (optional)

We will acknowledge receipt, investigate, and communicate resolution timeline. We do not currently offer a bug bounty program, but responsible disclosures are credited in our changelog.

---

## Supported Versions

| Component         | Version    | Security Support |
|-------------------|------------|-----------------|
| FastAPI Backend   | Current    | ✅ Active        |
| React Frontend    | 19.x       | ✅ Active        |
| PostgreSQL        | 16.x       | ✅ Active        |
| Python Runtime    | 3.12.x     | ✅ Active        |

Older deployed versions are not supported. Railway deployments are always on the current main branch.

---

## Security Principles

1. **Deterministic calculations are never delegated to AI.** Tax incentive calculations, compliance determinations, and jurisdiction rule logic are computed by the backend engine — not by Claude.
2. **AI is advisory only.** The Claude-powered AI Advisor provides guidance and suggestions. It does not approve rules, calculate tax credits, or make compliance decisions.
3. **Secrets never live in source code.** All credentials, API keys, and connection strings are managed via environment variables and Railway's secret management.
4. **Audit trails are non-negotiable.** All compliance-affecting actions are logged with actor, timestamp, and before/after state.
5. **Least privilege by default.** Every user role has only the permissions required for their function.

---

## Scope

This policy covers:
- `getsceneiq.com` and all subdomains
- `aura.getsceneiq.com`
- `contractreview.getsceneiq.com`
- Railway-hosted backend API services
- SceneIQ-Compliance platform
- SceneIQ Budget Builder
- AURA Enterprise screenplay analysis

---

## Out of Scope

- Third-party services (Stripe, Anthropic, Railway infrastructure, Cloudflare)
- Brevo email delivery infrastructure
- Social engineering attacks targeting personnel

---

## Security Contact

**Howard Neal, Founder & CEO**  
Scene Reader Studio Technologies LLC  
Chicago, IL  
security@getsceneiq.com

---

*See also: [Security Overview](docs/security/security-overview.md) | [Data Retention](docs/security/data-retention.md) | [Incident Response](docs/security/incident-response.md)*
