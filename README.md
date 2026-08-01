# SceneIQ
> Tax Incentive Intelligence for Film & TV

A full-stack compliance platform for discovering, stacking, and managing film and television production tax incentives across US states, counties, and international jurisdictions.

---

## Quick Start (Local)

**Requires:** Docker Desktop

```bash
docker compose up -d
```

Open `http://localhost:3000` — Login: <ADMIN_EMAIL> / <ADMIN_PASSWORD_EXAMPLE>  (do NOT commit real credentials)

---

## Production

**Live URL:** `https://taxincentivecomplianceplatform-production.up.railway.app`

Hosted on Railway with PostgreSQL. Auto-deploys on push to `main`.

---

## Features

| Feature | Description |
|---------|-------------|
| **Dashboard** | Budget volume, estimated credits, active productions, spend chart |
| **Productions** | Create and manage film/TV productions linked to jurisdictions |
| **Incentive Calculator** | Single-jurisdiction credit calculation |
| **Jurisdictions** | 23 state/country jurisdictions, 35+ incentive rules |
| **Scenario Calculator** | Compare 2–6 jurisdictions side-by-side, stacks state + local incentives, highlights best jurisdiction |
| **AI Advisor** | Claude-powered chat for qualification guidance and stacking strategies |
| **Georgia** | Dedicated Georgia incentive workspace |
| **MMB Connector** | CSV upload tool for Motion Picture Association data |
| **Production Schedule** | Import script breakdowns (CSV/MMS/FDX), build stripboard, generate DOOD + call sheets, track per-jurisdiction shoot days |
| **Transmission Log** | Broadcast schedule importer (CSV/XML/BXF/JSON) — what aired, when, and where |
| **Local Rules** | Approved county/city incentive rules (extracted by feed monitor) |
| **Rule Review** | Approve or reject AI-extracted rules before they go live |
| **Admin** | User and system management |

---

## Production Schedule Engine

Pre-production scheduling for film/TV: import a script breakdown, build the stripboard, generate the Day Out of Days and daily call sheets, and push verified per-jurisdiction shoot-day counts into[...]

**Sidebar:** Production Schedule → 5 sub-tabs (Import · Stripboard · Day Out of Days · Call Sheets · Jurisdiction Tracker).

### Supported import formats

| Format | Extension | Source |
|---|---|---|
| CSV breakdown | `.csv` | Movie Magic Budgeting, Showbiz Budgeting, Scenechronize, or any spreadsheet matching the column reference in the user guide |
| Movie Magic Scheduling | `.mms` | Movie Magic Scheduling — File → Export → XML |
| Final Draft | `.fdx` | Final Draft — File → Save As → Final Draft XML |

### API endpoints

All paths prefixed `/api/0.1.0/production-schedule/{production_id}` and require a JWT Bearer token:

| Verb | Path | Purpose |
|---|---|---|
| POST | `/import` | Upload + parse a script breakdown (CSV/MMS/FDX) |
| GET  | `/stripboard` | Full stripboard grid for the production |
| POST | `/stripboard/assign` | Pin a scene to a shoot day |
| GET  | `/dood` | Day Out of Days grid |
| GET  | `/dood/export?format=csv\|pdf` | DOOD download |
| GET  | `/call-sheet/{day_number}` | Call sheet JSON for one shoot day |
| GET  | `/call-sheet/{day_number}/pdf` | Call sheet PDF for one shoot day |
| GET  | `/jurisdiction-tracker` | Per-jurisdiction shoot-day summary |
| POST | `/compliance-bridge/push` | Push verified counts to the Incentive Calculator |

### Not to be confused with — Transmission Log

The Production Schedule Engine handles **pre-production shooting schedules** (what is *filmed*, by whom, on which day, in which jurisdiction). The **Transmission Log** (sidebar: Transmission Log) [...]

**Full operator guide:** [PRODUCTION_SCHEDULE_USER_GUIDE.md](PRODUCTION_SCHEDULE_USER_GUIDE.md).

---

## Sub-Jurisdictions

11 county/city jurisdictions with **additive stacking** on top of parent state rules:

- **CA-LA** — Los Angeles County
- **IL-COOK** — Cook County (Chicago)
- **NY-NYC / NY-BROOKLYN / NY-QUEENS / NY-MANHATTAN / NY-BRONX / NY-STATEN-ISLAND** — NYC boroughs
- **NY-ERIE / NY-NASSAU / NY-WESTCHESTER** — New York counties

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | React 19 · TypeScript · Vite 7 · Tailwind CSS v4 |
| Backend | FastAPI · Prisma ORM 0.15.0 · Python 3.12 |
| Database | PostgreSQL 16 |
| AI | Anthropic Claude (claude-sonnet-4-6) |
| Infra (local) | Docker · Nginx |
| Infra (prod) | Railway · Nixpacks |

---

## Local Services

| Service | Container | URL |
|---------|-----------|-----|
| Frontend | `pilotforge-ui` | http://localhost:3000 |
| Backend API | `pilotforge-api` | http://localhost:8001/api/0.1.0/ |
| Nginx proxy | `pilotforge-nginx` | http://localhost |
| PostgreSQL | `tax-incentive-db` | localhost:5432 |

---

## API

Base path: `/api/0.1.0/`
Interactive docs: `/api/0.1.0/docs`

Key endpoints:

```
POST /auth/login
GET  /jurisdictions/
GET  /incentive-rules/
POST /stacking-engine/compare
GET  /local-rules/
GET  /pending-rules/
GET  /health
```

All endpoints except `/auth/login` and `/health` require a JWT Bearer token.

---

## Railway Deployment

Required environment variables:

| Variable | Notes |
|----------|-------|
| `DATABASE_URL` | Link via `${{Postgres.DATABASE_URL}}` |
| `JWT_SECRET` | 256-bit hex secret |
| `SECRET_KEY` | 256-bit hex secret |
| `APP_ENV` | `production` |
| `ANTHROPIC_API_KEY` | Required for AI Advisor |

Build and start are configured in `railway.toml`. On first deploy, seed sub-jurisdictions via Railway shell:

```bash
python scripts/seed_sub_jurisdictions.py
python scripts/seed_more_sub_jurisdictions.py
```

---

## Docker Images

| Image | Tag |
|-------|-----|
| Backend | `hneal1038/pilotforge-backend:latest` |
| Frontend | `hneal1038/pilotforge-frontend:latest` |

---

## Documentation

- **[USER_MANUAL.md](USER_MANUAL.md)** — Full feature guide, API reference, deployment walkthrough
- **API Docs** — `/api/0.1.0/docs` (Swagger UI, live on running instance)

---

## Repository

- **Branch:** `main`
- **Docker Hub:** [hub.docker.com/u/hneal1038](https://hub.docker.com/u/hneal1038)
- **GitHub:** [hneal055/Tax_Incentive_Compliance_Platform](https://github.com/hneal055/Tax_Incentive_Compliance_Platform)
