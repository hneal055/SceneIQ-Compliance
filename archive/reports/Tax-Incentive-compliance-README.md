# SceneIQ
> Tax Incentive Intelligence for Film & TV

A full-stack compliance platform for managing film and television production tax incentives across 23 jurisdictions in the USA, Canada, and internationally.

---

## Quick Start

**Requires:** Docker Desktop running on Windows.

```powershell
.\start.ps1
```

Opens `http://localhost:3000` automatically. Login: `admin@pilotforge.com` / `pilotforge2024`

For full setup instructions, troubleshooting, and developer notes → **[SETUP_GUIDE.md](SETUP_GUIDE.md)**

---

## Features

- **Executive Dashboard** — budget volume, estimated credits, active projects, spend chart
- **Productions** — create and manage film/TV productions linked to jurisdictions
- **Incentive Calculator** — real-time credit calculation across all jurisdictions
- **Jurisdictions** — 39 jurisdictions, 35 incentive rules (USA, Canada, UK, EU, AU, NZ)
- **AI Advisor** — chat interface for jurisdiction comparisons, qualification guidance, stacking strategies
- **MMB Connector

## Tech Stack

| Layer    | Technology                                      |
| -------- | ----------------------------------------------- |
| Frontend | React 19 · TypeScript · Tailwind CSS v4 · Vite  |
| Backend  | FastAPI · Prisma ORM · Python 3.12              |
| Database | PostgreSQL 16                                   |
| Infra    | Docker · Nginx                                  |

## Docker Images

| Image    | Tag                                        |
| -------- | ------------------------------------------ |
| Backend  | `hneal1038/pilotforge-backend:latest`      |
| Frontend | `hneal1038/pilotforge-frontend:latest`     |

## Repository

- **Working branch:** `feature/test-ci`
- **Stable branch:** `main`
- **Docker Hub:** [hub.docker.com/u/hneal1038](https://hub.docker.com/u/hneal1038)
