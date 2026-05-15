# SceneIQ-Compliance — Broadcast Scheduler Parser Integration
# Claude Code Instruction Brief

---

## Context & Goal

You are integrating an existing standalone Python broadcast scheduler
parser into the SceneIQ-Compliance platform as a new feature module.

SceneIQ is a full-stack tax incentive compliance platform for film and
television production. The broadcast scheduler parser reads industry
schedule files (CSV, XML/BXF, JSON), validates and normalises the data,
and exports structured output.

These two tools are being integrated because broadcast schedule data
(what aired, when, on which channel, in which state/jurisdiction) feeds
directly into SceneIQ's production spend tracking and tax incentive
qualification workflows.

### Note — separate from the Production Schedule Engine

The Broadcast Scheduler module described in this document is for
**post-production broadcast scheduling** — what aired, when, on which
channel. It is distinct from the **Production Schedule Engine**
(sidebar: "Production Schedule"), which handles **pre-production
shooting schedules** — what is filmed, by whom, on which day, in
which jurisdiction. See
[PRODUCTION_SCHEDULE_USER_GUIDE.md](PRODUCTION_SCHEDULE_USER_GUIDE.md)
for that module. The two share the word "schedule" but operate at
opposite ends of the production lifecycle.

---

## Developer Profile

- Novice developer
- Tools: Python, PowerShell, VS Code
- Platform: Windows
- Existing familiarity: the parser codebase (built prior to this task)

---

## Source Repositories

- **SceneIQ-Compliance (target):**
  https://github.com/hneal055/SceneIQ-Compliance

- **Broadcast Scheduler Parser (source):**
  https://github.com/hneal055/broadcast-scheduler-parser
  (private repo — already cloned locally)

Both repos are already cloned locally and open in VS Code.

---

## Tech Stack — SceneIQ

| Layer      | Technology                                      |
|------------|-------------------------------------------------|
| Frontend   | React 19, TypeScript, Vite 7, Tailwind CSS v4   |
| Backend    | FastAPI, Python 3.12, Prisma ORM 0.15.0         |
| Database   | PostgreSQL 16                                   |
| AI         | Anthropic Claude (claude-sonnet-4-6)            |
| Local Infra| Docker, Nginx                                   |
| Prod Infra | Railway                                         |

---

## Integration Architecture

The parser becomes a backend service inside SceneIQ. A new React page
is added to the existing dashboard. No changes are made to existing
SceneIQ features.

### Target folder structure (new additions only):

```
SceneIQ-Compliance/
├── backend/
│   ├── routers/
│   │   └── schedule_parser.py        ← NEW: FastAPI router
│   └── services/
│       └── broadcast_scheduler/      ← NEW: parser as a service module
│           ├── __init__.py
│           ├── parsers/
│           │   ├── __init__.py
│           │   ├── csv_parser.py
│           │   ├── xml_parser.py
│           │   └── json_parser.py
│           ├── models/
│           │   ├── __init__.py
│           │   ├── schedule.py
│           │   ├── segment.py
│           │   └── asset.py
│           ├── processors/
│           │   ├── __init__.py
│           │   ├── validator.py
│           │   ├── transformer.py
│           │   └── exporter.py
│           ├── utils/
│           │   ├── __init__.py
│           │   ├── timecode.py
│           │   ├── date_helper.py
│           │   └── file_handler.py
│           └── config/
│               └── field_maps.py     ← NEW: field maps extracted from
│                                          standalone settings.py
├── dashboard-app/
│   └── src/
│       └── pages/
│           └── ScheduleParser/       ← NEW: React UI
│               ├── index.tsx
│               ├── UploadPanel.tsx
│               ├── ResultsTable.tsx
│               └── ExportPanel.tsx
└── prisma/
    └── schema.prisma                 ← EDIT: add ScheduleEvent model
```

---

## Integration Phases — Build in this exact order

---

### PHASE 1 — Repo Cleanup (SceneIQ root)

Before adding anything, clean up the SceneIQ root directory.

**Files to delete from root (safe to remove — not source code):**
- Any `.txt` files that contain git commands
  (e.g. `git clone httpsgithub.comttpsgithub.txt`,
   `git remote add origin httpsgithub.c.txt`)
- `.env.txt` (contains no real secrets — just example text)
- `.gitignore.backup`

**Folders to add to .gitignore (do not delete, just exclude):**
- `node_modules/`
- `Lib/site-packages/`
- `archive_20260218_125420/`
- `safety_backup_20260219_085731/`

**Commit message after cleanup:**
```
chore: repo cleanup before scheduler parser integration
```

**Rules:**
- Do NOT delete any `.md` files, source code, or config files
- Do NOT modify backend/, frontend/, dashboard-app/, prisma/, or scripts/
- Show a list of files to be deleted and wait for approval before deleting

---

### PHASE 2 — Copy Parser as Backend Service

Copy the parser source files from the standalone repo into
`backend/services/broadcast_scheduler/`.

**Steps:**
1. Create the folder `backend/services/broadcast_scheduler/`
2. Copy these folders from the standalone parser repo into it:
   - `parsers/`
   - `models/`
   - `processors/`
   - `utils/`
3. Create `backend/services/broadcast_scheduler/__init__.py` (empty)
4. Create `backend/services/broadcast_scheduler/config/field_maps.py`
   by extracting ONLY the field map dictionaries from the standalone
   `config/settings.py`:
   - `CSV_FIELD_MAP`
   - `XML_FIELD_MAP`
   - `JSON_FIELD_MAP`
   Add a comment at the top: "Add new field name variants here as
   new schedule formats are encountered."
5. Update all imports inside the copied files:
   - Replace `from config.settings import ...` with imports from
     `backend/services/broadcast_scheduler/config/field_maps.py`
   - Replace path-based settings (INPUT_DIR, OUTPUT_DIR, etc.) with
     values passed in at call time — do not hardcode paths

**Rules:**
- Do not modify the standalone parser repo
- Do not copy `config/settings.py` or `config/logging_config.py`
  (SceneIQ has its own logging and config)
- Do not copy `scripts/`, `tests/`, `data/`, or `docs/`
- Show a diff of all import changes before writing

---

### PHASE 3 — Add Prisma Schema Model

Add a `ScheduleEvent` model to `prisma/schema.prisma` so that parsed
segments can be stored in the SceneIQ PostgreSQL database.

**Add this model:**

```prisma
model ScheduleEvent {
  id              String   @id @default(cuid())
  channel         String
  scheduleDate    String?
  sourceFile      String
  sourceFormat    String   // "csv", "xml", or "json"
  title           String
  episodeTitle    String?
  episodeNumber   String?
  seriesNumber    String?
  txTime          String?
  duration        String?
  genre           String?
  rightsStart     String?
  rightsEnd       String?
  assetId         String?
  daypart         String?  // derived from txTime by date_helper
  importedAt      DateTime @default(now())
  productionId    String?  // optional link to SceneIQ Production model
}
```

After editing schema.prisma, run:
```
npx prisma migrate dev --name add_schedule_event
```

Show the migration output and confirm it ran cleanly before proceeding.

---

### PHASE 4 — FastAPI Router

Create `backend/routers/schedule_parser.py` with three endpoints:

**1. POST /schedule/upload**
- Accepts a file upload (CSV, XML, or JSON)
- Detects format from file extension
- Calls the correct parser from `broadcast_scheduler/parsers/`
- Runs `transform_schedule()` then `validate_schedule()`
- Saves each segment as a `ScheduleEvent` row in PostgreSQL via Prisma
- Returns a JSON summary:
  `{ channel, date, segments_parsed, errors, warnings, events_saved }`

**2. GET /schedule/events**
- Returns a paginated list of saved ScheduleEvent rows
- Supports optional query params: `channel`, `date`, `source_format`
- Default page size: 50

**3. DELETE /schedule/events/{id}**
- Deletes a single ScheduleEvent by ID
- Returns `{ deleted: true, id }`

**Rules:**
- Follow the same router pattern as existing SceneIQ routers
- Require JWT Bearer token (same auth as all other SceneIQ endpoints)
- Wrap all database calls in try/except — never crash the API
- Add the new router to `backend/main.py` under the prefix
  `/api/0.1.0/schedule`
- Log all upload events (file name, format, segment count, errors)

---

### PHASE 5 — React Dashboard Page

Create a new Schedule Parser page in the existing React dashboard.

**Files to create:**

`dashboard-app/src/pages/ScheduleParser/index.tsx`
- Page title: "Schedule Parser"
- Contains UploadPanel at top, ResultsTable below
- Matches the visual style of existing SceneIQ dashboard pages
  (same Tailwind classes, same card/panel layout as Productions page)

`dashboard-app/src/pages/ScheduleParser/UploadPanel.tsx`
- Drag-and-drop file upload area
- Accepts .csv, .xml, .bxf, .json only
- Shows file name and detected format after selection
- Upload button triggers POST /schedule/upload
- Shows a loading spinner during upload
- Displays the summary response (segments parsed, errors, warnings)
  in a colour-coded result box:
  - Green if 0 errors
  - Yellow if warnings only
  - Red if errors

`dashboard-app/src/pages/ScheduleParser/ResultsTable.tsx`
- Calls GET /schedule/events on load
- Displays results in a table with columns:
  Channel, Date, Title, TX Time, Duration, Daypart, Format, Imported
- Supports filter by channel and date
- Matches the table style used elsewhere in SceneIQ dashboard

**Navigation:**
- Add "Schedule Parser" as a nav item in the existing sidebar
- Use an appropriate icon from the icon set already used in SceneIQ
- Place it after "MMB Connector" in the nav order

**Rules:**
- Do NOT create a new design system — reuse existing Tailwind classes
  and component patterns from the SceneIQ dashboard
- Do NOT install new npm packages without noting them in the response
- Use the same API client pattern already used in other SceneIQ pages
  for authenticated fetch calls

---

### PHASE 6 — Verification & Commit

Run a full end-to-end test:

1. Start SceneIQ locally: `docker compose up -d`
2. Confirm all existing features still work (login, dashboard, productions)
3. Upload `tests/sample_data/sample_rundown.csv` via the new UI
4. Confirm the summary shows: 6 segments, 0 errors, 1 warning
5. Confirm rows appear in the Results Table
6. Repeat with `sample_rundown.xml` and `sample_rundown.json`
7. Confirm 18 total rows in the database (6 per format)
8. Check the SceneIQ API docs at `/api/0.1.0/docs` — confirm the
   three new schedule endpoints appear

If all checks pass, create the commit:
```
git add .
git commit -m "feat: broadcast scheduler parser integrated as schedule module"
git push origin main
```

If any check fails, fix before committing. Do not commit broken code.

---

## General Rules for Claude Code

- Use Plan mode before writing any files in each phase
- After each phase, summarise what was built and what comes next
- Never modify existing SceneIQ features, routes, or components
- Never delete files without listing them and waiting for approval
- Never hardcode file paths — use relative paths or environment variables
- If a decision affects the database schema or existing API contracts,
  stop and ask before proceeding
- Keep all new Python code beginner-friendly with comments above
  every function
- If a package needs to be installed, state the install command and
  wait for confirmation before running it

---

## Definition of Done

- [ ] Repo root cleaned up
- [ ] Parser copied into backend/services/broadcast_scheduler/
- [ ] All imports updated and tested
- [ ] ScheduleEvent model in Prisma, migration run cleanly
- [ ] Three FastAPI endpoints working with JWT auth
- [ ] New router registered in main.py
- [ ] React Schedule Parser page built and styled to match SceneIQ
- [ ] Nav item added to sidebar
- [ ] End-to-end test passes: 18 segments across 3 formats
- [ ] All existing SceneIQ features unaffected
- [ ] Clean commit pushed to main