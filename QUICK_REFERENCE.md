# SceneIQ — Quick Reference

## Access

| Environment | URL | Login |
|-------------|-----|-------|
| Local | http://localhost:3000 | <ADMIN_EMAIL> / <ADMIN_PASSWORD_EXAMPLE> |
| Production | https://taxincentivecomplianceplatform-production.up.railway.app | <ADMIN_EMAIL> / <ADMIN_PASSWORD_EXAMPLE> |
| API Docs | http://localhost:8001/api/0.1.0/docs | (requires login token) |

---

## Local Docker — Daily Commands

```bash
# Start everything
docker compose up -d

# Stop everything
docker compose down

# View logs
docker logs pilotforge-api --tail 50 -f
docker logs pilotforge-ui --tail 20

# Container health
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
```

---

## Services

| Container | Role | Port |
|-----------|------|------|
| `pilotforge-api` | FastAPI backend | 8001 |
| `pilotforge-ui` | React frontend (nginx) | 3000 |
| `pilotforge-nginx` | Reverse proxy | 80 |
| `tax-incentive-db` | PostgreSQL 16 | 5432 |

---

## Deploy Code Changes (without image rebuild)

```bash
# Backend — copy file + restart
docker cp src/api/my_file.py pilotforge-api:/app/src/api/my_file.py
docker restart pilotforge-api

# Frontend — build + copy dist
cd frontend && npm run build
docker cp dist/. pilotforge-ui:/usr/share/nginx/html/
docker exec pilotforge-ui nginx -s reload

# Backend schema change (Prisma) — full rebuild required
docker compose build backend
docker compose up -d backend
```

---

## Database

```bash
# Connect to local DB
docker exec -it tax-incentive-db psql -U postgres -d tax_incentive_db

# Apply pending migrations
docker exec pilotforge-api python -m prisma migrate deploy

# Regenerate Prisma client (after schema.prisma change)
docker exec pilotforge-api python -m prisma generate

# Re-seed sub-jurisdictions
docker exec pilotforge-api python scripts/seed_sub_jurisdictions.py
docker exec pilotforge-api python scripts/seed_more_sub_jurisdictions.py
```

---

## Feed Monitor

```bash
# Test a single jurisdiction (no DB write)
python monitor.py --code NY-ERIE --dry-run

# Run all jurisdictions
python monitor.py

# Mock Claude extraction (no API billing)
MOCK_CLAUDE=true python monitor.py
```

Logs → `logs/monitor.log`
Scheduled daily at 6 AM via Windows Task Scheduler (`scripts/schedule_monitor.ps1`)

---

## API — Key Endpoints

```bash
TOKEN="eyJ..."   # from POST /auth/login

# Login
curl -X POST http://localhost:8001/api/0.1.0/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"<ADMIN_EMAIL>","password":"<ADMIN_PASSWORD_EXAMPLE>"}'

# Health (no auth)
curl http://localhost:8001/health

# Jurisdictions
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8001/api/0.1.0/jurisdictions/

# Scenario Calculator — compare 2 jurisdictions
curl -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  http://localhost:8001/api/0.1.0/stacking-engine/compare \
  -d '{
    "scenarios": [
      {"jurisdiction_code": "CA-LA", "qualified_spend": 5000000},
      {"jurisdiction_code": "IL-COOK", "qualified_spend": 5000000}
    ]
  }'
```

---

## Railway — Environment Variables

| Variable | Notes |
|----------|-------|
| `DATABASE_URL` | `${{Postgres.DATABASE_URL}}` |
| `JWT_SECRET` | 256-bit hex (generate: `python -c "import secrets; print(secrets.token_hex(32))"`) |
| `SECRET_KEY` | 256-bit hex (same method) |
| `APP_ENV` | `production` |
| `ANTHROPIC_API_KEY` | Required for AI Advisor |

---

## Jurisdictions

**23 state/country:** CA, GA, NY, LA, NM, IL, MI, NJ, VA, CO, HI, OR, MT, MS, BC, ON, QC, UK, AU, IE, FR, ES, NZ

**11 sub-jurisdictions (county/city):**

| Code | Name | Parent |
|------|------|--------|
| CA-LA | Los Angeles County | CA |
| IL-COOK | Cook County | IL |
| NY-NYC | New York City | NY |
| NY-BROOKLYN | Brooklyn | NY |
| NY-QUEENS | Queens | NY |
| NY-MANHATTAN | Manhattan | NY |
| NY-BRONX | Bronx | NY |
| NY-STATEN-ISLAND | Staten Island | NY |
| NY-ERIE | Erie County | NY |
| NY-NASSAU | Nassau County | NY |
| NY-WESTCHESTER | Westchester County | NY |

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| 404 on Railway after push | Wait ~5 min for Railway deploy; check deploy logs |
| `FieldNotFoundError` on Prisma field | `docker exec pilotforge-api python -m prisma generate` |
| Frontend shows stale code | Rebuild: `cd frontend && npm run build` then copy dist |
| `prisma migrate deploy` fails with P3009 | Run `bash scripts/resolve_migration.sh` |
| AI Advisor returns no response | Check `ANTHROPIC_API_KEY` is set; use `MOCK_CLAUDE=true` to test pipeline |
| Port 3000 already in use | Dev stack is running; demo stack uses port 3001 |

---

## Full Documentation

- **[README.md](README.md)** — Project overview
- **[USER_MANUAL.md](USER_MANUAL.md)** — Feature guide, API reference, deployment walkthrough
