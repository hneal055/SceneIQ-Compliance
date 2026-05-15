# Production Schedule Sample Fixtures

Test fixtures for the Production Schedule Engine importers. Each fixture
ships in three formats so cross-format import parity stays exercisable.

## Fixture matrix

| Fixture | Scenes | Cast | Locations | Jurisdictions | TOD mix | What it stress-tests |
|---|---|---|---|---|---|---|
| `sample_breakdown.{csv,mms,fdx}` | 10 | 6 | 6 | 1 (GA) | DAY | Canonical Neon Pulse baseline; `seed_pse_assignments.py` reads this. Don't move or rename. |
| `neon_pulse/breakdown.{csv,mms,fdx}` | — | — | — | — | — | Reserved subfolder for future variant edits; mirrors the canonical baseline above. |
| `midnight_harbour/breakdown.{csv,mms,fdx}` | 6 | 5 | 5 | 1 (GA) | DAWN / DAY / NIGHT / DUSK | Small noir thriller. Tests DAWN/DUSK timecodes, page-half-counts (0.125, 0.5, 0.75), single no-cast insert, small-cast scenes. |
| `locked_room/breakdown.{csv,mms,fdx}` | 8 | 3 | **1** | 1 (NM) | All NIGHT | Bottle episode. Tests stripboard with identical location 8× in a row, single-cast solo beat, all-NIGHT shoot, long dialogue scenes (3-4.5 pages). |
| `continental_express/breakdown.{csv,mms,fdx}` | 15 | 10 | 12 | **3 (GA / LA / NM)** | DAWN / DAY / DUSK / NIGHT | Multi-state action travel. Tests Jurisdiction Tracker with 3 rows, compliance push spanning states, 2 no-cast B-roll cutaways, full timecode variety. |
| `silver_falls/breakdown.{csv,mms,fdx}` | 20 | 14 | 8 | 1 (LA) | All NIGHT | Large ensemble period drama. Tests big DOOD grid (14 rows), 7-person ensemble call sheet (scene 20), long scenes (5.5-6 pages), repeated location reuse, all-NIGHT scheduling. |

## Behaviour notes by format

**CSV** — Full breakdown semantics. Page counts, jurisdiction, notes, all
present. Use this format when testing end-to-end behaviour against any
fixture.

**MMS** — Mirror of the CSV. Same scene numbers, locations, cast, and
page counts. One `<ProductionNote>` element per scene is intentionally
unmapped to verify silent-ignore behaviour.

**FDX** — Screenplay semantics. **No page counts** (FDX is a script
export, not a breakdown — the importer leaves `page_count` as `None`).
**No jurisdiction column** — to test jurisdiction-dependent endpoints
using an FDX fixture, upload the matching CSV/MMS instead, or assign
jurisdiction after import. Cast is derived from `<Paragraph
Type="Character">` blocks; the importer cleans V.O. / O.S.
parentheticals.

## Tests that consume these fixtures

- [tests/test_stripboard.py](../test_stripboard.py) reads
  `sample_breakdown.csv` directly. Keep that filename stable.
- Pure-compute tests (`test_dood.py`, `test_call_sheet.py`,
  `test_jurisdiction_tracker.py`, `test_compliance_bridge.py`) build
  their own in-memory dataclass fixtures and do not read these files.
- [tests/test_production_schedule_router.py](../test_production_schedule_router.py)
  is a smoke-level test and does not read these files.

## Manual demo flow per fixture

For each fixture below, replace `{fixture}/breakdown.csv` with the path
you want to upload.

```powershell
$PROD = "<production-uuid>"
$TOKEN = (curl -s -X POST http://localhost/api/0.1.0/auth/login `
  -H "Content-Type: application/json" `
  -d '{"email":"admin@pilotforge.com","password":"pilotforge2024"}' `
  | python -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

curl -s -X POST "http://localhost/api/0.1.0/production-schedule/$PROD/import" `
  -H "Authorization: Bearer $TOKEN" `
  -F "file=@tests/sample_data/continental_express/breakdown.csv"
```

## Adding a new fixture

1. Pick a subfolder name (`fixture_name/` — snake_case).
2. Create the three files: `breakdown.csv`, `breakdown.mms`,
   `breakdown.fdx`.
3. Match scene numbers, locations, and cast across all three formats so
   they import to the same canonical set.
4. Add a row to the matrix above describing what your fixture stresses.
5. Run the parsers via the snippet in `tests/sample_data/README.md` (or
   via `python -c "from src.services.production_schedule.importers.csv_importer
   import parse_csv_breakdown; print(len(parse_csv_breakdown('path')))"`)
   to confirm the parsed scene count matches expectations.
