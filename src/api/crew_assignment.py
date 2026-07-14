"""
crew_assignment.py - Phase 5 Slice 5: Crew Assignment & Coverage Engine
GET /productions/{id}/crew/assignment-analysis

Derives per-day crew assignments from availability (startDate/endDate
windows; crew with no dates are treated as run-of-show) and detects
coverage gaps: core departments with no available crew on a day, and
special requirements inferred from day and scene notes (stunt -> Stunts,
vfx -> VFX, etc.) that the roster cannot cover. Fires per-day
crew_coverage_gap signals using the standard dedupe/auto-resolve
lifecycle. Report-only: assignments are computed, never persisted.
"""
import logging
from typing import List, Optional
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from datetime import datetime, timezone

from src.utils.database import prisma

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Crew Intelligence"])

# Departments expected on set every shoot day (only enforced if the
# roster has ever had that department - a production with no Sound
# department hired yet shouldn't get 7 identical gap flags).
_CORE_DEPARTMENTS = ["Camera", "Electric", "Grip", "Sound", "AD"]

# Keyword -> required department, scanned in day notes and scene notes
_REQUIREMENT_KEYWORDS = {
    "stunt": "Stunts",
    "vfx": "VFX",
    "pyro": "Special Effects",
    "sfx": "Special Effects",
    "animal": "Animal Wrangler",
    "minor": "Studio Teacher",
    "underwater": "Marine",
}


def _parse_date(value):
    if not value:
        return None
    if isinstance(value, datetime):
        return value.date()
    try:
        return datetime.strptime(str(value).strip()[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


class DayCoverage(BaseModel):
    day_number: int
    date: Optional[str]
    available_crew: int
    departments_covered: List[str]
    required_special: List[str]
    missing_departments: List[str]
    requirement_sources: List[str]
    covered: bool


class CrewAvailability(BaseModel):
    name: str
    role: str
    department: str
    available_days: int
    total_days: int
    run_of_show: bool


class AssignmentResponse(BaseModel):
    production_id: str
    production_title: str
    total_shoot_days: int
    crew_count: int
    roster_departments: List[str]
    days_fully_covered: int
    days_with_gaps: int
    signals_created: int
    signals_resolved: int
    days: List[DayCoverage]
    crew: List[CrewAvailability]


@router.get(
    "/productions/{production_id}/crew/assignment-analysis",
    response_model=AssignmentResponse,
    summary="Per-day crew coverage, availability, and requirement gaps",
)
async def analyze_assignments(production_id: str):
    production = await prisma.production.find_unique(where={"id": production_id})
    if not production:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Production not found")

    shoot_days = await prisma.shootday.find_many(
        where={"productionId": production_id},
        order={"dayNumber": "asc"},
    )
    if not shoot_days:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No shoot days")

    crew = await prisma.crewmember.find_many(
        where={"productionId": production_id, "status": "active"},
    )
    if not crew:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active crew members - seed crew before running assignment analysis",
        )

    scenes = await prisma.scene.find_many(where={"productionId": production_id})
    scenes_by_day: dict = {}
    for s in scenes:
        if s.shootDayId:
            scenes_by_day.setdefault(s.shootDayId, []).append(s)

    roster_departments = sorted({c.department for c in crew})

    # Availability windows
    crew_windows = []
    for c in crew:
        start = _parse_date(c.startDate)
        end = _parse_date(c.endDate)
        crew_windows.append((c, start, end))

    def available_on(day_date, start, end):
        # Run-of-show (no dates) is always available; if the day itself
        # has no date, availability can't be constrained -> available.
        if day_date is None:
            return True
        if start and day_date < start:
            return False
        if end and day_date > end:
            return False
        return True

    existing_signals = await prisma.productionsignal.find_many(
        where={
            "productionId": production_id,
            "signalType": "crew_coverage_gap",
            "source": "crew_engine",
            "resolved": False,
        }
    )
    existing_by_day = {sig.entityId: sig for sig in existing_signals}

    days_out: List[DayCoverage] = []
    availability_count = {c.id: 0 for c in crew}
    signals_created = 0
    signals_resolved = 0
    gap_day_ids = set()

    for day in shoot_days:
        day_date = _parse_date(day.date)

        # Who is available today, grouped by department
        depts_today = set()
        avail = 0
        for c, start, end in crew_windows:
            if available_on(day_date, start, end):
                avail += 1
                depts_today.add(c.department)
                availability_count[c.id] += 1

        # Special requirements from day notes + scene notes
        required_special = set()
        sources = []
        texts = []
        if day.notes:
            texts.append(("day notes", day.notes))
        for s in scenes_by_day.get(day.id, []):
            if s.notes:
                texts.append((f"scene {s.sceneNumber}", s.notes))
        for src_label, text in texts:
            lower = text.lower()
            for kw, dept in _REQUIREMENT_KEYWORDS.items():
                if kw in lower and dept not in required_special:
                    required_special.add(dept)
                    sources.append(f"{dept} <- {src_label}: '{kw}'")

        # Gaps: core departments (that exist on the roster) missing today,
        # plus special requirements the roster has no department for.
        missing = []
        for dept in _CORE_DEPARTMENTS:
            if dept in roster_departments and dept not in depts_today:
                missing.append(dept)
        for dept in sorted(required_special):
            if dept not in depts_today:
                missing.append(dept)

        covered = len(missing) == 0
        days_out.append(DayCoverage(
            day_number=day.dayNumber,
            date=day.date,
            available_crew=avail,
            departments_covered=sorted(depts_today),
            required_special=sorted(required_special),
            missing_departments=missing,
            requirement_sources=sources,
            covered=covered,
        ))

        # --- Per-day gap signal ---
        if not covered:
            gap_day_ids.add(day.id)
            safety = any(d in ("Stunts", "Special Effects", "Marine") for d in missing)
            severity = "high" if safety else "medium"
            day_label = f"Day {day.dayNumber}" + (f" ({day.date})" if day.date else "")
            message = (
                f"Crew coverage gap: {day_label} is missing "
                f"{', '.join(missing)}. "
                + (f"Requirements detected from: {'; '.join(sources)}. " if sources else "")
                + f"{avail} crew available across {len(depts_today)} departments. "
                + ("Safety-relevant department missing - resolve before shooting."
                   if safety else "Hire or reassign to cover before this day.")
            )
            if day.id in existing_by_day:
                await prisma.productionsignal.update(
                    where={"id": existing_by_day[day.id].id},
                    data={"severity": severity, "message": message},
                )
            else:
                await prisma.productionsignal.create(
                    data={
                        "productionId": production_id,
                        "signalType":   "crew_coverage_gap",
                        "severity":     severity,
                        "source":       "crew_engine",
                        "entityType":   "shoot_day",
                        "entityId":     day.id,
                        "message":      message,
                    }
                )
                signals_created += 1

    # Auto-resolve signals for days no longer gapped
    for day_id, sig in existing_by_day.items():
        if day_id not in gap_day_ids:
            await prisma.productionsignal.update(
                where={"id": sig.id},
                data={
                    "resolved": True,
                    "resolvedAt": datetime.now(timezone.utc),
                    "resolvedBy": "crew_engine",
                },
            )
            signals_resolved += 1

    crew_out = [
        CrewAvailability(
            name=c.name, role=c.role, department=c.department,
            available_days=availability_count[c.id],
            total_days=len(shoot_days),
            run_of_show=(s is None and e is None),
        )
        for (c, s, e) in crew_windows
    ]

    fully = sum(1 for d in days_out if d.covered)
    return AssignmentResponse(
        production_id=production_id,
        production_title=production.title,
        total_shoot_days=len(shoot_days),
        crew_count=len(crew),
        roster_departments=roster_departments,
        days_fully_covered=fully,
        days_with_gaps=len(days_out) - fully,
        signals_created=signals_created,
        signals_resolved=signals_resolved,
        days=days_out,
        crew=crew_out,
    )
