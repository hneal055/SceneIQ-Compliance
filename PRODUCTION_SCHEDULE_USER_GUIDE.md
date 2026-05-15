# Production Schedule — User Guide

> For line producers, 1st ADs, UPMs, and production coordinators using the SceneIQ Production Schedule module. Plain language, no developer jargon.

---

## Table of Contents

1. [What this module does](#1-what-this-module-does)
2. [How to import a script breakdown](#2-how-to-import-a-script-breakdown)
3. [Building your stripboard](#3-building-your-stripboard)
4. [Generating the Day Out of Days](#4-generating-the-day-out-of-days)
5. [Generating call sheets](#5-generating-call-sheets)
6. [Understanding the Jurisdiction Tracker](#6-understanding-the-jurisdiction-tracker)
7. [Pushing data to the compliance layer](#7-pushing-data-to-the-compliance-layer)
8. [Troubleshooting common import issues](#8-troubleshooting-common-import-issues)
9. [CSV template field reference](#9-csv-template-field-reference)

---

## 1. What this module does

The Production Schedule module is the pre-production workspace inside SceneIQ. You bring in your script breakdown, group scenes into shoot days, and let SceneIQ generate the standard delivery documents your production needs every morning: the Day Out of Days for cast scheduling, daily call sheets for crew, and a running per-jurisdiction shoot-day count for tax incentive qualification.

Everything in this module is keyed to a **Production**. Pick the production from the dropdown at the top of the page and all five sub-tabs (Import, Stripboard, Day Out of Days, Call Sheets, Jurisdiction Tracker) operate on that production.

> **Note — this is not the Transmission Log.** The Transmission Log (different sidebar tab) is for broadcast scheduling — what aired on what channel at what time. The Production Schedule is for *pre-production* scheduling — what gets filmed, by whom, on which day, in which jurisdiction. Same word "schedule", two different phases of the production lifecycle.

The module covers five jobs:

- **Import** a script breakdown from your scheduling software.
- **Build a stripboard** — group scenes by shoot day, in shooting order.
- **Generate the Day Out of Days (DOOD)** for cast scheduling.
- **Generate daily call sheets** as PDF or live dashboard view.
- **Track per-jurisdiction shoot days** and push verified counts into the Incentive Calculator so your tax credit estimate stays current as the schedule evolves.

---

## 2. How to import a script breakdown

The Import sub-tab accepts three file formats: **CSV**, **MMS** (Movie Magic Scheduling), and **FDX** (Final Draft). SceneIQ detects the format from the file extension. Drag the file into the upload zone (or click to browse), confirm the detected format, and click **Upload & Parse**.

A green success panel appears when the import succeeds. It shows the number of scenes imported and a chip for each jurisdiction SceneIQ detected from your scene locations.

### CSV — script-breakdown spreadsheet

Most line producers will use this one. Any breakdown export from **Movie Magic Budgeting**, **Showbiz Budgeting**, **Scenechronize**, or a custom Google Sheet/Excel spreadsheet works as long as the column headers match the reference in Section 9.

A workable minimum CSV needs four columns: Scene #, Title, Location, Pages. Add Int/Ext, Day/Night, Cast, Jurisdiction, and Notes as you have them.

If your headers don't match exactly, see the [troubleshooting section](#8-troubleshooting-common-import-issues).

### MMS — Movie Magic Scheduling

If your AD is already running Movie Magic Scheduling, you can export the schedule directly:

1. In Movie Magic Scheduling, open your schedule.
2. **File → Export → XML** (sometimes labelled "Export to XML" or "Save As .mms").
3. Save the file somewhere accessible.
4. Drag the `.mms` file into the SceneIQ Import zone.

SceneIQ reads the scene number, heading, description, pages, set name, cast/element list, and notes. It silently ignores production-only metadata (camera notes, director notes, budget codes).

### FDX — Final Draft

If you're earlier in pre-production and only have the script, Final Draft can export an FDX (Final Draft XML) file:

1. In Final Draft, open your screenplay.
2. **File → Save As → Final Draft XML (.fdx)**.
3. Drag the `.fdx` file into the SceneIQ Import zone.

SceneIQ reads each scene heading (INT/EXT, location, day/night), counts the pages, and pulls character names from the dialogue. Cast lists from an FDX import are derived from who has dialogue in each scene — they will be less precise than a proper breakdown export from MMS, but it's a reasonable starting point.

### What happens after import

The Import panel will show the count of scenes parsed and the jurisdictions SceneIQ recognized from the location text. The scenes are now in the system but **not yet grouped into shoot days** — that happens in the Stripboard tab.

---

## 3. Building your stripboard

The Stripboard tab shows your scenes grouped into shoot days. Each **DAY block** displays the day number, the shoot date, the location, the total pages for that day (in eighths), and a cast-count badge showing how many speaking parts are needed.

Click a DAY block's chevron to expand it and see the scene strips. Each strip shows the scene number, slugline, page count, and a coloured indicator for the scene type (interior/exterior, day/night, action vs dialogue).

### Reading page eighths

Page counts display in eighths, the industry standard:

- A half-page scene shows as **4/8**, not 0.5.
- A scene that runs one-and-a-quarter pages shows as **1 2/8**.
- A two-page scene shows as **2**.

A typical full shooting day for a feature is around **5 to 6 pages** total. Use the per-day page total at the top of each DAY block to gauge whether you're overloaded.

### Expand and collapse

Two buttons at the top of the Stripboard let you **Expand All** or **Collapse All** days at once. By default, days start collapsed so you can scan the whole shoot at a glance.

### A current-release limitation

Drag-and-drop scene reordering and day-reassignment is **not yet wired into this release**. For now, scenes arrive grouped into shoot days based on the import. The "Add scene to Day N" button is visible but disabled — a tooltip explains it. A future release will add interactive reordering.

If you need to move a scene to a different day today, that has to happen in your source scheduling software (Movie Magic Scheduling or your CSV) and then re-import.

---

## 4. Generating the Day Out of Days

The Day Out of Days (DOOD) is the cast-scheduling grid that's been an industry standard since well before software existed. Rows are cast members; columns are shoot days; each cell holds a single-letter status code.

Open the **Day Out of Days** sub-tab. SceneIQ derives the grid automatically from the scenes-to-days assignments and the cast list of each scene.

### Reading the codes

| Code | Meaning |
|---|---|
| **S** | Start — first day this cast member is needed |
| **W** | Work — cast member is on call and used |
| **H** | Hold — between work days, paid but not used |
| **F** | Finish — last day this cast member is needed |
| **SW** | Start + Work — first day, and also works that day |
| **WF** | Work + Finish — works on the last day |
| **SWF** | Start + Work + Finish — starts and finishes on the same day (a one-day part) |

Cells outside a cast member's first-to-last window are left blank. A cast member who never appears in a scheduled scene is omitted from the grid entirely.

### Exporting the grid

Two buttons at the top right:

- **Export CSV** downloads a spreadsheet you can open in Excel or hand to payroll. The CSV includes a date row under the day numbers so it's readable on its own.
- **Export PDF** downloads a landscape letter-size PDF with the same grid, colour-coded by status (work-coded cells in green, hold in amber, start/finish in blue). This is the version you'd hand to your DP or PM.

---

## 5. Generating call sheets

The Call Sheets sub-tab generates a daily call sheet for any shoot day. Pick the day number from the day selector at the top; SceneIQ generates the call sheet on the fly.

### The seven sections

Every call sheet covers the same seven sections, in the same order:

1. **General Info** — production title, episode (if applicable), day number, date.
2. **General Call** — the crew call time as a large prominent badge. This is the time most departments need to be on set.
3. **Location** — the shoot location and address.
4. **Nearest Hospital** — the closest hospital for incident response, by industry safety standard.
5. **Weather** — placeholder unless populated. (Weather isn't auto-fetched in the current release; the PM fills it in the morning of the shoot.)
6. **Scenes** — the day's scenes in a 7-column table: scene #, title, location, Int/Ext, Day/Night, pages, and cast list.
7. **Crew Calls** — department-by-department call times, when populated. (Departmental staggering isn't auto-generated in the current release; the AD fills these in.)

### PDF vs dashboard view

- The **dashboard view** is what you see in the Call Sheets sub-tab. Sections render as cards. Useful at your desk; you can scroll, switch days, and refresh as the schedule changes.
- The **PDF view** is for distribution. Click **Download PDF** — SceneIQ generates a portrait letter-size PDF that you can email, print, or attach to a digital call-sheet tool like Croogloo or Set Hero.

Both views read the same underlying data, so if the dashboard view shows a stale call sheet, regenerate the PDF.

---

## 6. Understanding the Jurisdiction Tracker

The Jurisdiction Tracker is where the pre-production schedule meets tax-incentive compliance. Each row is one jurisdiction (e.g. Georgia, Louisiana, New Mexico). The columns are:

- **Jurisdiction** — name and internal ID.
- **Shoot Days** — how many days of your schedule are pinned to this jurisdiction.
- **Verified At** — when the count was last marked verified.
- **Status** — Verified (green pill) or Unverified (amber pill).

### Why per-jurisdiction shoot days matter

Most tax-incentive programs have a **minimum-day threshold** for qualification. Georgia, for example, requires the production to spend a minimum number of qualifying days in-state. The Jurisdiction Tracker is how SceneIQ tracks that as your stripboard evolves — drop a scene from Georgia to Louisiana and the count updates the next time you save.

### Verified vs Unverified

The Verified pill appears once the row has been confirmed. In the current release, rows are auto-marked Verified at creation time — a manual "Verify this row" workflow is a future enhancement, intended for the line producer or production accountant to attest that the count matches the actual booked days. Treat the current pill as informational, not a compliance attestation.

### Refreshing the table

The **Refresh** button at the top right re-reads the latest counts. Use it after a stripboard change.

---

## 7. Pushing data to the compliance layer

The **Push to Compliance Bridge** button (top right of the Jurisdiction Tracker tab) is the handoff between the Production Schedule module and the rest of SceneIQ's tax-incentive workflow.

### What it does

Clicking Push sends the current per-jurisdiction shoot-day counts to the **Incentive Calculator**. The Calculator uses those counts to:

- Evaluate qualification — has the production met each jurisdiction's minimum-day threshold?
- Update its credit estimate — knowing the actual shoot-day distribution sharpens the credit math.
- Surface flags — if a count drops below a threshold mid-shoot, the Calculator can warn you.

A round-trip in plain terms:

```
Stripboard  →  Jurisdiction Tracker  →  [Push]  →  Incentive Calculator
(what's     →  (how many days        →           →  (does that pass each
 shot       →   per jurisdiction)    →           →   jurisdiction's
 where)                                              qualification gate?)
```

After a successful push you'll see a green confirmation panel showing how many records were pushed. Open the Incentive Calculator for the same production to see the updated count reflected in the calculation.

### When to push

Push after any meaningful change to the schedule — new scenes added, days moved between jurisdictions, days added or removed. There's no harm in pushing more often; the Calculator simply uses the latest snapshot.

---

## 8. Troubleshooting common import issues

### "Imported 0 scenes"

**Symptom:** Upload succeeds, success panel shows 0 scenes.

**Cause:** Your CSV column headers don't match any of the accepted headers in Section 9.

**Fix:** Open your CSV in Excel/Google Sheets. Check the first row against the **Accepted Headers** column in Section 9. Rename your columns to match one of the accepted variants. The matching is case-sensitive; "Scene Number" works, "scene number" does not. Re-save as CSV and re-upload.

### "Jurisdiction not detected" — empty jurisdiction chips

**Symptom:** Import succeeds, but the success panel shows no jurisdiction chips, or fewer than expected.

**Cause:** The text in your Location/Jurisdiction column doesn't match a jurisdiction in SceneIQ's catalogue. SceneIQ matches against jurisdiction names ("Georgia", "Louisiana") and codes ("GA", "LA").

**Fix:** Confirm your Jurisdiction or State column uses recognized names or two-letter codes. Open the Jurisdictions tab in the sidebar to see the full catalogue. If your location is a county/city (e.g. "Cook County"), make sure the parent state is also present.

### "Cast column shows ID strings, not character names"

**Symptom:** Call sheet PDF or dashboard view shows long random-looking IDs in the Cast column instead of character names like "MARSH" or "ROOKIE".

**Cause:** A known limitation in the current release. The import flow doesn't yet create matched cast records for the names it reads from your breakdown. Without that match, downstream documents can't resolve IDs back to readable names.

**Fix:** This is on the Phase 11.5 follow-up list and will be addressed in a near-term release. As a workaround for an urgent demo or print, ask your SceneIQ administrator to backfill the cast records manually.

### "DOOD / Call Sheet empty after import"

**Symptom:** Import succeeds, but the Day Out of Days or Call Sheets tab shows an empty state.

**Cause:** The import created scene records but those scenes aren't yet assigned to specific shoot days. The DOOD and Call Sheets are derived from the **scene-to-day** assignments, not from raw scenes.

**Fix:** Today, this means making sure the imported schedule already groups scenes into shoot days (every scene needs a Day column or equivalent). MMS exports from a properly built schedule will include this. A bare FDX import won't — you'd need to add day assignments in your source before re-importing. Interactive drag-and-drop reassignment in the Stripboard is on the same Phase 11.5 list.

### "Push to Compliance Bridge returns no data"

**Symptom:** You click Push and the panel doesn't show pushed records.

**Cause:** No Jurisdiction Tracker rows have been created yet for this production. The Push button operates on those rows.

**Fix:** Confirm the Jurisdiction Tracker table is populated. If it's empty even after you've assigned scenes to shoot days with jurisdictions set, this is the same Phase 11.5 follow-up — the assign workflow doesn't yet roll up into the Jurisdiction Tracker aggregate. A near-term release will fix this automatically.

---

## 9. CSV template field reference

The CSV importer accepts any header variant listed in the left column below. Headers are case-sensitive; leading and trailing whitespace is trimmed.

| Accepted Headers | Internal Field | Description / Example |
|---|---|---|
| `Scene Number`, `Scene #`, `Scene No`, `Scene No.` | Scene number | The script scene number. Accepts non-numeric values like `12A`, `INSERT-3`. Example: `12A`. |
| `Scene Title`, `Title`, `Slugline` | Title | The scene slugline or short title. Example: `INTERROGATION ROOM A — DAY`. |
| `Location`, `Set`, `Setting` | Location | The set/location name. Example: `POLICE STATION BULLPEN`. |
| `Int/Ext`, `INT/EXT`, `I/E` | Interior/Exterior | One of `INT`, `EXT`, or `INT/EXT`. Example: `INT`. |
| `Day/Night`, `Time`, `TOD` | Time of day | One of `DAY`, `NIGHT`, `DAWN`, `DUSK`. Example: `DAY`. |
| `Page Count`, `Pages`, `Eighths` | Page count | Decimal page count where 1.0 = one full page (i.e. 8/8). A half-page scene is `0.5`. Example: `2.125` (= 2 pages and 1/8). |
| `Cast`, `Characters`, `Cast List` | Cast list | Comma-separated character names. Example: `MARSH, ROOKIE, CAPTAIN HOLT`. |
| `Jurisdiction`, `Location State`, `State` | Jurisdiction | Recognized jurisdiction name (`Georgia`) or two-letter code (`GA`). Example: `Georgia`. |
| `Notes`, `Comments`, `Production Notes` | Notes | Free-text scene notes. Example: `Hero's wide entrance — extras needed`. |

### Complete example row

A minimum CSV with all recommended columns:

```csv
Scene Number,Title,Location,Int/Ext,Day/Night,Pages,Cast,Jurisdiction,Notes
1,POLICE STATION - OPENING,POLICE STATION,INT,DAY,2.5,"MARSH, ROOKIE, CAPTAIN HOLT",Georgia,Wide establishing shot
2,BULLPEN - MORNING BRIEFING,POLICE STATION BULLPEN,INT,DAY,3.125,"MARSH, ROOKIE, CAPTAIN HOLT, DET. CHEN",Georgia,Coffee setup needed
3,CAPTAIN'S OFFICE - ORDERS,CAPTAIN HOLT OFFICE,INT,DAY,1.875,"MARSH, CAPTAIN HOLT",Georgia,
4,INTERROGATION INTRO,INTERROGATION ROOM A,INT,DAY,2.25,"MARSH, ROOKIE, SUSPECT",Georgia,
```

### Adding new header variants

If your scheduling software exports a header SceneIQ doesn't yet recognize, ask your SceneIQ administrator to add it to the field map. New variants slot into `src/services/production_schedule/config/field_maps.py` (a one-line addition); no code changes are required elsewhere.

---

## Further reading

- [README.md](README.md) — SceneIQ overview, deployment, full feature list.
- [USER_MANUAL.md](USER_MANUAL.md) — Long-form internal manual covering every SceneIQ feature.
- [sceneiq_scheduler_integration.md](sceneiq_scheduler_integration.md) — Brief for the separate Transmission Log (broadcast) module, for distinction.
