# SceneIQ — Production Schedule Engine
# Claude Code Integration Brief
# Version 1.0 — May 2026

---

## Context & Goal

You are building the Production Schedule Engine — a new integrated
module for the SceneIQ Unified Compliance Platform (UCP). This is the
third and most complex layer of the platform, sitting above the existing
Compliance layer and feeding verified shoot day data directly into the
Tax Incentive Calculator.

SceneIQ already has:
- Compliance layer: Incentive Calculator, Scenario Calculator, AI Advisor,
  Jurisdictions, MMB Connector, Local Rules, Rule Review
- Broadcast layer: Broadcast Transmission Log Importer (in integration)

This build adds:
- Production layer: Script Breakdown, Stripboard, Day Out of Days,
  Call Sheet Generator, Jurisdiction Shoot Day Tracker, Compliance Bridge

---

## Critical Distinction — Two Types of Schedules

This module handles PRODUCTION SHOOTING SCHEDULES only:
  - Scenes, shoot days, cast availability, crew call times, locations
  - Used by: directors, ADs, line producers, production coordinators
  - Tools it replaces: Movie Magic Scheduling, spreadsheet stripboards

It is ENTIRELY SEPARATE from the Broadcast Transmission Log Importer,
which handles BROADCASTER PLAYOUT SCHEDULES:
  - What episodes aired on TV, when, and on which channel
  - Used by: broadcast operations, traffic, compliance teams

Never conflate these two. Document the distinction clearly in all
comments, docstrings, and user-facing labels.

---

## Developer Profile

- Novice developer
- Tools: Python, PowerShell, VS Code, Docker
- Platform: Windows
- Existing familiarity: SceneIQ codebase, broadcast scheduler parser

---

## Repository

- SceneIQ-Compliance: https://github.com/hneal055/SceneIQ-Compliance
- Tech stack: React 19 + TypeScript + FastAPI + Python 3.12 +
  PostgreSQL 16 + Prisma ORM + Docker + Railway

---

## Architecture — New Additions Only

```
SceneIQ-Compliance/
├── backend/
│   ├── routers/
│   │   └── production_schedule.py     NEW: FastAPI router
│   └── services/
│       └── production_schedule/       NEW: core engine
│           ├── __init__.py
│           ├── importers/
│           │   ├── __init__.py
│           │   ├── mms_importer.py    Movie Magic Scheduling
│           │   ├── fdx_importer.py    Final Draft
│           │   └── csv_importer.py    SceneIQ CSV template
│           ├── models/
│           │   ├── __init__.py
│           │   ├── scene.py           Scene data class
│           │   ├── shoot_day.py       ShootDay data class
│           │   ├── cast_member.py     CastMember data class
│           │   └── call_sheet.py      CallSheet data class
│           ├── generators/
│           │   ├── __init__.py
│           │   ├── stripboard.py      Stripboard builder
│           │   ├── dood.py            Day Out of Days generator
│           │   └── call_sheet.py      Call sheet generator (PDF + JSON)
│           ├── trackers/
│           │   ├── __init__.py
│           │   └── jurisdiction_tracker.py  Shoot days per jurisdiction
│           └── bridge/
│               ├── __init__.py
│               └── compliance_bridge.py     Feeds data to calculator
├── dashboard-app/
│   └── src/
│       └── pages/
│           └── ProductionSchedule/    NEW: React UI
│               ├── index.tsx
│               ├── ImportPanel.tsx
│               ├── Stripboard.tsx
│               ├── DayOutOfDays.tsx
│               ├── CallSheetViewer.tsx
│               └── JurisdictionTracker.tsx
└── prisma/
    └── schema.prisma                  EDIT: add new models
```

---

## Data Models — Add to prisma/schema.prisma

### Scene
```prisma
model Scene {
  id              String    @id @default(cuid())
  productionId    String
  sceneNumber     String
  title           String?
  location        String?
  locationType    String?   // INT or EXT
  timeOfDay       String?   // DAY, NIGHT, DAWN, DUSK
  pageCount       Float?
  jurisdictionId  String?
  castIds         String[]
  notes           String?
  shootDayId      String?
  createdAt       DateTime  @default(now())
}
```

### ShootDay
```prisma
model ShootDay {
  id              String    @id @default(cuid())
  productionId    String
  dayNumber       Int
  date            String?
  jurisdictionId  String?
  scenes          Scene[]
  totalPages      Float?
  callTime        String?
  location        String?
  nearestHospital String?
  notes           String?
  createdAt       DateTime  @default(now())
}
```

### CastMember
```prisma
model CastMember {
  id              String    @id @default(cuid())
  productionId    String
  characterName   String
  actorName       String?
  doodEntries     Json?     // { "2026-01-15": "W", "2026-01-16": "H" }
  startDay        Int?
  finishDay       Int?
  createdAt       DateTime  @default(now())
}
```

### CallSheet
```prisma
model CallSheet {
  id              String    @id @default(cuid())
  productionId    String
  shootDayId      String
  dayNumber       Int
  date            String?
  generalCall     String?
  location        String?
  nearestHospital String?
  weather         String?
  scenes          Json?
  crewCalls       Json?
  createdAt       DateTime  @default(now())
}
```

### JurisdictionShootDays
```prisma
model JurisdictionShootDays {
  id              String    @id @default(cuid())
  productionId    String
  jurisdictionId  String
  shootDays       Int       @default(0)
  verifiedAt      DateTime  @default(now())
  updatedAt       DateTime  @updatedAt
}
```

After editing schema.prisma run:
```
npx prisma migrate dev --name add_production_schedule_engine
```
Confirm migration ran cleanly before proceeding.

---

## Build Phases — in this exact order

---

### PHASE 1 — Data Models & Prisma

Add all 5 models above to prisma/schema.prisma.
Create the Python data classes in:
  backend/services/production_schedule/models/

Each Python class should mirror the Prisma model.
Add a comment above every class and every field.
Use simple Python dataclasses — no complex inheritance.
Run the migration and confirm it passes before Phase 2.

---

### PHASE 2 — CSV Importer (simplest first)

Create a SceneIQ standard CSV import template and importer.

CSV template columns (create as sample_breakdown.csv in tests/):
  Scene Number, Scene Title, Location, Int/Ext, Day/Night,
  Page Count, Cast, Jurisdiction, Notes

importer: backend/services/production_schedule/importers/csv_importer.py
Functions:
  parse_csv_breakdown(filepath)
    Opens the CSV, returns a list of Scene objects.
    Handles missing columns gracefully — log and skip, never crash.
    Uses utf-8-sig to handle Excel BOM (same as broadcast parser).

  build_scene_from_row(row, field_map)
    Translates one CSV row into a Scene object.
    Strips whitespace, converts empty cells to None.

Also create a CSV_SCENE_FIELD_MAP in a new config file:
  backend/services/production_schedule/config/field_maps.py
  Map common column name variants to internal Scene field names.
  Examples: "INT/EXT" -> "loc_type", "Scene #" -> "scene_number"

Test with sample_breakdown.csv. Confirm scenes parse correctly.

---

### PHASE 3 — Movie Magic Scheduling Importer

Movie Magic Scheduling exports .mms files which are XML-based.
Create: backend/services/production_schedule/importers/mms_importer.py

Functions:
  parse_mms_file(filepath)
    Opens and parses the MMS XML structure.
    Extracts scenes, elements, and breakdown tags.
    Returns a list of Scene objects.
    Wraps everything in try/except — never crash on malformed files.

  find_scenes_in_mms(root_element)
    Navigates the MMS XML tree to find scene nodes.
    Handles both single-scene and multi-scene structures.

  build_scene_from_mms_element(element)
    Maps MMS XML tags to Scene fields using MMS_FIELD_MAP.

Add MMS_FIELD_MAP to config/field_maps.py.
Create a sample .mms test file in tests/sample_data/.

Note: If a real .mms file is not available, build the importer
to the MMS XML spec and note that live testing requires a real file.

---

### PHASE 4 — Final Draft Importer

Final Draft .fdx files are XML. Scene headings contain location,
int/ext, and day/night. Character names appear in dialogue elements.

Create: backend/services/production_schedule/importers/fdx_importer.py

Functions:
  parse_fdx_file(filepath)
    Opens the FDX file and extracts scene headings and characters.
    Returns a list of Scene objects — one per scene heading.
    Scene title derived from the scene heading text.
    Cast derived from unique character names within each scene.

  extract_scene_heading(element)
    Parses a scene heading like "INT. POLICE STATION - DAY"
    Returns: loc_type="INT", location="POLICE STATION", time_of_day="DAY"

  extract_cast_from_scene(scene_element)
    Returns a list of unique character names from dialogue elements
    within a scene.

Create a sample .fdx test file in tests/sample_data/ with 5 scenes.
Test that headings parse into correct loc_type, location, time_of_day.

---

### PHASE 5 — Stripboard Builder

Create: backend/services/production_schedule/generators/stripboard.py

The stripboard organises scenes into shoot days. Each shoot day
has an ordered list of scenes, a total page count, and a jurisdiction.

Functions:
  build_stripboard(scenes, shoot_days)
    Takes a list of Scene objects and a list of ShootDay objects.
    Returns the full stripboard structure as a dict:
      { day_number: { date, jurisdiction, scenes[], total_pages } }

  assign_scene_to_day(scene, shoot_day)
    Links a scene to a shoot day. Updates scene.shoot_day_id.

  calculate_day_pages(shoot_day, scenes)
    Sums page counts for all scenes assigned to a shoot day.
    Returns the total as a float.

  reorder_scenes_in_day(shoot_day_id, scene_ids_ordered)
    Accepts a new scene order and updates the database.
    Used by the drag-and-drop frontend.

  get_stripboard_summary(production_id)
    Returns: total shoot days, total scenes, total pages,
    shoot days per jurisdiction.

---

### PHASE 6 — Day Out of Days Generator

Create: backend/services/production_schedule/generators/dood.py

The DOOD is a grid showing each cast member's status for every
shoot day. Standard codes:
  S = Start, W = Work, H = Hold, T = Travel, F = Finish,
  SW = Start + Work, WF = Work + Finish

Functions:
  generate_dood(production_id, cast_members, shoot_days)
    Returns a 2D grid:
      { cast_member_id: { day_number: "W", day_number: "H", ... } }
    Infers codes from scene assignments in the stripboard.

  export_dood_csv(dood_grid, cast_members, shoot_days)
    Writes the DOOD grid as a CSV file.
    Header row: Cast Member, Day 1 date, Day 2 date, etc.
    One row per cast member.
    Returns file path.

  export_dood_pdf(dood_grid, cast_members, shoot_days)
    Generates a formatted PDF using reportlab or fpdf2.
    Include production title, date generated, and page number.
    Returns file path.

Install fpdf2 if not already installed. Note the install command
and wait for approval.

---

### PHASE 7 — Call Sheet Generator

Create: backend/services/production_schedule/generators/call_sheet.py

Functions:
  generate_call_sheet(shoot_day, scenes, crew_calls, production)
    Builds a CallSheet object from shoot day data.
    Saves it to the database.
    Returns the CallSheet object.

  export_call_sheet_pdf(call_sheet)
    Generates a formatted PDF call sheet using fpdf2.
    Sections: General Info, Scenes, Cast Calls, Crew Calls,
    Location, Nearest Hospital, Weather.
    Returns file path.

  export_call_sheet_json(call_sheet)
    Returns the call sheet as a JSON dict for the live dashboard view.

Call sheet PDF must include:
  - Production title and episode number
  - Shoot day number and date
  - General crew call time
  - Location name and full address
  - Nearest hospital name and address
  - Weather (placeholder field — populated manually or via API later)
  - Scene list: scene number, title, location, int/ext, day/night, pages, cast
  - Crew department calls table

---

### PHASE 8 — Jurisdiction Shoot Day Tracker

Create:
  backend/services/production_schedule/trackers/jurisdiction_tracker.py

Functions:
  count_shoot_days_per_jurisdiction(production_id, shoot_days)
    Reads jurisdiction assignments from shoot days in the stripboard.
    Returns a dict: { jurisdiction_id: shoot_day_count }
    Updates the JurisdictionShootDays table in the database.

  get_jurisdiction_summary(production_id)
    Returns a formatted summary for the dashboard:
      [ { jurisdiction_id, jurisdiction_name, shoot_days, verified_at } ]

  verify_shoot_days(production_id)
    Marks the current shoot day counts as verified.
    Sets verified_at timestamp on each JurisdictionShootDays record.
    Verified counts can be passed to the Compliance Bridge.

---

### PHASE 9 — Compliance Bridge

Create:
  backend/services/production_schedule/bridge/compliance_bridge.py

This is the critical integration layer. It passes verified shoot day
data from the Production Schedule Engine into the existing
SceneIQ compliance calculation layer.

Functions:
  push_shoot_days_to_calculator(production_id)
    Reads verified JurisdictionShootDays records for the production.
    Updates the production record with shoot day counts per jurisdiction.
    These counts are then available to the Incentive Calculator
    and Scenario Calculator when running credit calculations.

  reconcile_with_mmb(production_id)
    Compares shoot day count per jurisdiction from the stripboard
    against spend data from the MMB Connector.
    Returns a reconciliation report:
      { jurisdiction, shoot_days_from_stripboard,
        spend_days_from_mmb, match: true/false, variance }

  get_compliance_data_summary(production_id)
    Returns a combined summary of:
      - Verified shoot days per jurisdiction
      - Qualified spend per jurisdiction (from MMB)
      - Estimated credit per jurisdiction (from calculator)
    Used to populate the full compliance report.

---

### PHASE 10 — FastAPI Router

Create: backend/routers/production_schedule.py

Endpoints:

POST /production-schedule/import
  Accepts a file upload (.csv, .mms, .fdx)
  Detects format from extension
  Calls the correct importer
  Saves scenes to the database
  Returns: { scenes_imported, jurisdictions_detected, warnings }

GET /production-schedule/{production_id}/stripboard
  Returns the full stripboard structure for a production

POST /production-schedule/{production_id}/stripboard/assign
  Assigns a scene to a shoot day
  Body: { scene_id, shoot_day_id, position }

GET /production-schedule/{production_id}/dood
  Returns the Day Out of Days grid

GET /production-schedule/{production_id}/dood/export
  Query param: format=csv or format=pdf
  Returns the DOOD as a downloadable file

GET /production-schedule/{production_id}/call-sheet/{day_number}
  Returns the call sheet for a specific shoot day as JSON

GET /production-schedule/{production_id}/call-sheet/{day_number}/pdf
  Returns the call sheet as a downloadable PDF

GET /production-schedule/{production_id}/jurisdiction-tracker
  Returns shoot day counts per jurisdiction

POST /production-schedule/{production_id}/compliance-bridge/push
  Pushes verified shoot day data to the compliance layer

Rules:
  Follow existing SceneIQ router patterns
  Require JWT Bearer token on all endpoints
  Wrap all database calls in try/except
  Register router in backend/main.py under /api/0.1.0/production-schedule
  Log all import events (file, format, scene count, warnings)

---

### PHASE 11 — React Dashboard Pages

Create: dashboard-app/src/pages/ProductionSchedule/

Files:

index.tsx
  Page title: "Production Schedule"
  Sub-navigation tabs: Import, Stripboard, Day Out of Days,
  Call Sheets, Jurisdiction Tracker
  Matches SceneIQ dashboard visual style throughout

ImportPanel.tsx
  Drag-and-drop upload for .csv, .mms, .fdx files
  Shows detected format and scene count after import
  Colour-coded result box (green/yellow/red)
  Lists imported scenes in a preview table

Stripboard.tsx
  Visual grid — rows = scenes, columns = shoot days
  Colour-coded by jurisdiction
  Shows total pages per day
  Drag-and-drop reordering calls POST stripboard/assign
  Jurisdiction day count summary shown below the grid

DayOutOfDays.tsx
  Grid table — rows = cast members, columns = shoot days
  Colour-coded cells by DOOD code (W=green, H=yellow, T=blue)
  Export buttons: CSV and PDF

CallSheetViewer.tsx
  Shoot day selector (dropdown or day number input)
  Renders call sheet sections: General Info, Scenes, Cast, Crew,
  Location, Hospital, Weather
  PDF download button
  Matches the live dashboard data from the API

JurisdictionTracker.tsx
  Table: jurisdiction, shoot days, verified status, last updated
  Verify button triggers POST compliance-bridge/push
  Shows reconciliation status vs MMB data if available

Navigation:
  Add "Production Schedule" to the sidebar
  Place it above "Schedule Parser" (now renamed
  "Transmission Log" in the sidebar)
  Use an appropriate icon from the existing SceneIQ icon set

Rules:
  Do NOT create a new design system
  Reuse existing Tailwind classes and component patterns
  Use the same API client pattern as other SceneIQ pages
  Do NOT install new npm packages without noting them first

---

### PHASE 12 — Verification & Commit

End-to-end test:

1. Start SceneIQ: docker compose up -d
2. Confirm all existing features still work
3. Import sample_breakdown.csv — confirm scenes parsed and saved
4. Assign scenes to shoot days in the stripboard
5. Confirm jurisdiction tracker counts update automatically
6. Generate a Day Out of Days — confirm CSV and PDF export
7. Generate a call sheet for Day 1 — confirm PDF and live view
8. Push shoot days to compliance bridge
9. Confirm Incentive Calculator receives updated shoot day counts
10. Check /api/0.1.0/docs — all new endpoints appear

If all checks pass:
```
git add .
git commit -m "feat: production schedule engine integrated into SceneIQ UCP"
git push origin main
```

---

### PHASE 13 — Documentation

Update all project documentation:

1. Update SceneIQ README.md
   Add Production Schedule Engine section
   List all features and supported import formats
   Note the distinction between shooting schedules and
   broadcast transmission schedules

2. Create PRODUCTION_SCHEDULE_USER_GUIDE.md in SceneIQ root
   Plain-language guide for line producers and ADs
   Sections:
     What this module does
     How to import a script breakdown (CSV, MMS, FDX)
     Building your stripboard
     Generating the Day Out of Days
     Generating call sheets (PDF and dashboard)
     Understanding the Jurisdiction Tracker
     Pushing data to the compliance layer
     Troubleshooting common import issues

3. Update SCENEIQ_SCHEDULER_INTEGRATION.md
   Add a note that the Broadcast Transmission Log Importer
   is distinct from this Production Schedule Engine

4. Commit:
   git add .
   git commit -m "docs: production schedule engine documentation and user guide"
   git push origin main

---

## General Rules for Claude Code

- Use Plan mode before writing any files in each phase
- After each phase summarise what was built and what comes next
- Never modify existing SceneIQ features, routes, or components
- Never delete files without listing them first and waiting for approval
- Never hardcode file paths — use relative paths or environment variables
- If a decision affects the database schema or existing API contracts,
  stop and ask before proceeding
- Keep all Python code beginner-friendly with comments above every function
- If a package needs to be installed, state the install command and
  wait for confirmation before running it
- Build one phase at a time — do not skip ahead
- After each phase confirm that existing SceneIQ features still work

---

## Definition of Done

- [ ] All 5 Prisma models added and migration run cleanly
- [ ] CSV importer working with sample_breakdown.csv
- [ ] Movie Magic Scheduling importer built to MMS XML spec
- [ ] Final Draft importer parsing scene headings and cast correctly
- [ ] Stripboard builder organising scenes into shoot days
- [ ] Day Out of Days generating CSV and PDF exports
- [ ] Call Sheet generator producing PDF and JSON output
- [ ] Jurisdiction Shoot Day Tracker counting days per jurisdiction
- [ ] Compliance Bridge pushing verified data to the calculator
- [ ] FastAPI router with all endpoints registered in main.py
- [ ] React dashboard pages built and styled to match SceneIQ
- [ ] Sidebar navigation updated
- [ ] End-to-end test passes across all 10 verification checks
- [ ] All existing SceneIQ features unaffected
- [ ] README.md updated
- [ ] PRODUCTION_SCHEDULE_USER_GUIDE.md created
- [ ] Clean commit pushed to main
