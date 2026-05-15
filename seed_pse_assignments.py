"""
Throwaway: fully reset Production Schedule Engine state for the
"Neon Pulse" production and seed it from tests/sample_data/sample_breakdown.csv.

Steps:
  1. Wipe Scene / ShootDay / CastMember / JurisdictionShootDays rows.
  2. Re-parse sample_breakdown.csv via the importer (pure compute).
  3. Insert 10 fresh Scene rows + 6 CastMember rows (normalized from
     character names).
  4. Create 3 ShootDay rows (2026-06-01..03, all Georgia).
  5. Distribute the 10 scenes across the 3 days (3/3/4), rewriting
     scene.castIds to point at CastMember.id values.
  6. Insert a JurisdictionShootDays row: Georgia = 3 days.

Not committed.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, ".")
from src.services.production_schedule.importers.csv_importer import parse_csv_breakdown
from src.utils.database import prisma


CSV_PATH = Path("tests/sample_data/sample_breakdown.csv")


async def main():
    await prisma.connect()
    try:
        prod = await prisma.production.find_first(where={"title": "Neon Pulse"})
        if prod is None:
            print("ERROR: no production titled 'Neon Pulse'", file=sys.stderr)
            return 1

        georgia = (
            await prisma.jurisdiction.find_first(where={"code": "GA"})
            or await prisma.jurisdiction.find_first(where={"name": "Georgia"})
        )
        if georgia is None:
            print("ERROR: no jurisdiction with code='GA' or name='Georgia'", file=sys.stderr)
            return 1

        print(f"Production: {prod.title} ({prod.id})")
        print(f"Jurisdiction: {georgia.name} ({georgia.id})")

        # 1. Wipe all PSE state for this production.
        # Order matters: clear scene.shootDayId before deleting ShootDay,
        # delete child rows (CallSheet) referencing ShootDay first, then
        # delete the rows themselves.
        wiped = await prisma.scene.delete_many(where={"productionId": prod.id})
        print(f"Wiped {wiped} Scene rows")
        wiped = await prisma.callsheet.delete_many(where={"productionId": prod.id})
        print(f"Wiped {wiped} CallSheet rows")
        wiped = await prisma.shootday.delete_many(where={"productionId": prod.id})
        print(f"Wiped {wiped} ShootDay rows")
        wiped = await prisma.castmember.delete_many(where={"productionId": prod.id})
        print(f"Wiped {wiped} CastMember rows")
        wiped = await prisma.jurisdictionshootdays.delete_many(where={"productionId": prod.id})
        print(f"Wiped {wiped} JurisdictionShootDays rows")

        # 2. Re-parse the fixture.
        parsed = parse_csv_breakdown(CSV_PATH)
        print(f"Parsed {len(parsed)} scenes from {CSV_PATH.name}")
        if len(parsed) != 10:
            print(f"WARNING: expected 10 scenes, got {len(parsed)}", file=sys.stderr)

        # 3. Create CastMember rows from unique character names.
        unique_names = []
        seen = set()
        for ds in parsed:
            for name in (ds.cast_ids or []):
                if name and name not in seen:
                    seen.add(name)
                    unique_names.append(name)
        name_to_id = {}
        for name in unique_names:
            cm = await prisma.castmember.create(
                data={"productionId": prod.id, "characterName": name},
            )
            name_to_id[name] = cm.id
        print(f"Created {len(unique_names)} CastMember rows")

        # 4. Create 3 ShootDay rows (all Georgia).
        day_specs = [
            ("2026-06-01", "07:00 AM", "Atlanta - Stage A"),
            ("2026-06-02", "06:30 AM", "Atlanta - Downtown Loft"),
            ("2026-06-03", "07:00 AM", "Atlanta - Rooftop"),
        ]
        days = []
        for i, (date, call, loc) in enumerate(day_specs, start=1):
            d = await prisma.shootday.create(
                data={
                    "productionId": prod.id,
                    "dayNumber": i,
                    "date": date,
                    "jurisdictionId": georgia.id,
                    "callTime": call,
                    "location": loc,
                    "nearestHospital": "Emory University Hospital Midtown",
                }
            )
            days.append(d)

        # 5. Insert scenes with shootDay assignment + FK-normalized castIds.
        buckets = [parsed[0:3], parsed[3:6], parsed[6:10]]
        for day, bucket in zip(days, buckets):
            total = 0.0
            for ds in bucket:
                fk_cast = [name_to_id[n] for n in (ds.cast_ids or []) if n in name_to_id]
                await prisma.scene.create(
                    data={
                        "productionId": prod.id,
                        "sceneNumber": ds.scene_number or "",
                        "title": ds.title,
                        "location": ds.location,
                        "locationType": ds.location_type,
                        "timeOfDay": ds.time_of_day,
                        "pageCount": ds.page_count,
                        "jurisdictionId": georgia.id,
                        "castIds": fk_cast,
                        "shootDayId": day.id,
                    }
                )
                total += ds.page_count or 0.0
            await prisma.shootday.update(
                where={"id": day.id},
                data={"totalPages": total},
            )
            print(f"  Day {day.dayNumber}: {len(bucket)} scenes, {total} pages")

        # 6. JurisdictionShootDays aggregate.
        await prisma.jurisdictionshootdays.create(
            data={
                "productionId": prod.id,
                "jurisdictionId": georgia.id,
                "shootDays": len(days),
            },
        )
        print(f"JurisdictionShootDays: Georgia = {len(days)} days")

        print("Done.")
    finally:
        await prisma.disconnect()


asyncio.run(main())
