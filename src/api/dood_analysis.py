"""
dood_analysis.py - Phase 5 Slice 4: DOOD Optimization Engine
GET /productions/{id}/cast/dood-analysis

Builds the Day Out of Days grid from scene-to-day assignments and
scene cast links. For each cast member: work days (W), hold days (H,
paid idle days between first and last work day), and hold cost at
the actor's daily rate. Computes the theoretical minimum holds under
optimal day ordering (a lower bound: each actor's work compressed to
consecutive days) and reports the reorder savings opportunity. Fires
per-actor hold_day_waste signals for actors with material hold cost,
using the standard dedupe/auto-resolve lifecycle.
"""
import logging
from typing import List, Optional
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from datetime import datetime, timezone

from src.utils.database import prisma

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Crew Intelligence"])

# Signal when a single actor's hold cost exceeds this
_HOLD_SIGNAL_THRESHOLD = 1000.0
# Default daily rate when a cast member has none set
_DEFAULT_CAST_RATE = 650.0


class CastDood(BaseModel):
    character: str
    actor: Optional[str]
    daily_rate: float
    work_days: List[int]
    first_day: int
    last_day: int
    span_days: int
    hold_days: List[int]
    hold_count: int
    hold_cost: float
    min_possible_holds: int
    dood_row: str  # e.g. "W H H W - - -"


class DoodResponse(BaseModel):
    production_id: str
    production_title: str
    total_shoot_days: int
    cast_count: int
    cast_with_scenes: int
    total_work_days: int
    total_hold_days: int
    total_hold_cost: float
    min_possible_hold_days: int
    reorder_savings_opportunity: float
    signals_created: int
    signals_resolved: int
    cast: List[CastDood]


@router.get(
    "/productions/{production_id}/cast/dood-analysis",
    response_model=DoodResponse,
    summary="Day Out of Days analysis: hold-day waste and reorder opportunity",
)
async def analyze_dood(production_id: str):
    production = await prisma.production.find_unique(where={"id": production_id})
    if not production:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Production not found")

    shoot_days = await prisma.shootday.find_many(
        where={"productionId": production_id},
        order={"dayNumber": "asc"},
    )
    if not shoot_days:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No shoot days")
    day_numbers = [d.dayNumber for d in shoot_days]
    day_by_id = {d.id: d.dayNumber for d in shoot_days}

    scenes = await prisma.scene.find_many(where={"productionId": production_id})
    cast_rows = await prisma.castmember.find_many(
        where={"productionId": production_id},
        order={"characterName": "asc"},
    )

    # cast member id -> set of day numbers they work
    works: dict = {c.id: set() for c in cast_rows}
    for s in scenes:
        if not s.shootDayId or not s.castIds:
            continue
        day_num = day_by_id.get(s.shootDayId)
        if day_num is None:
            continue
        for cid in s.castIds:
            if cid in works:
                works[cid].add(day_num)

    existing_signals = await prisma.productionsignal.find_many(
        where={
            "productionId": production_id,
            "signalType": "hold_day_waste",
            "source": "crew_engine",
            "resolved": False,
        }
    )
    existing_by_cast = {sig.entityId: sig for sig in existing_signals}

    cast_out: List[CastDood] = []
    total_work = 0
    total_holds = 0
    total_hold_cost = 0.0
    min_total_holds = 0
    signals_created = 0
    signals_resolved = 0
    signaled_ids = set()

    for c in cast_rows:
        wdays = sorted(works.get(c.id, set()))
        if not wdays:
            continue
        rate = c.dailyRate if (c.dailyRate and c.dailyRate > 0) else _DEFAULT_CAST_RATE

        first, last = wdays[0], wdays[-1]
        span = [n for n in day_numbers if first <= n <= last]
        holds = [n for n in span if n not in wdays]

        # Lower bound: if days could be reordered freely, this actor's
        # work compresses to consecutive days -> zero holds. The bound
        # per actor is 0; production-level bound is 0 too, but the
        # honest number reported is the per-actor current-vs-zero gap.
        min_holds = 0

        hold_cost = len(holds) * rate
        total_work += len(wdays)
        total_holds += len(holds)
        total_hold_cost += hold_cost
        min_total_holds += min_holds

        dood_row = " ".join(
            "W" if n in wdays else ("H" if n in holds else "-")
            for n in day_numbers
        )

        cast_out.append(CastDood(
            character=c.characterName,
            actor=c.actorName,
            daily_rate=round(rate, 2),
            work_days=wdays,
            first_day=first, last_day=last,
            span_days=len(span),
            hold_days=holds,
            hold_count=len(holds),
            hold_cost=round(hold_cost, 2),
            min_possible_holds=min_holds,
            dood_row=dood_row,
        ))

        # --- Per-actor signal ---
        if hold_cost >= _HOLD_SIGNAL_THRESHOLD:
            signaled_ids.add(c.id)
            message = (
                f"Hold-day waste: {c.characterName} works days "
                f"{', '.join(str(n) for n in wdays)} but is held (paid, idle) on "
                f"days {', '.join(str(n) for n in holds)} - {len(holds)} hold "
                f"day(s) at ${rate:,.0f}/day = ${hold_cost:,.0f}. Reordering shoot "
                f"days to cluster this actor's scenes could eliminate these holds."
            )
            if c.id in existing_by_cast:
                await prisma.productionsignal.update(
                    where={"id": existing_by_cast[c.id].id},
                    data={"severity": "medium", "message": message},
                )
            else:
                await prisma.productionsignal.create(
                    data={
                        "productionId": production_id,
                        "signalType":   "hold_day_waste",
                        "severity":     "medium",
                        "source":       "crew_engine",
                        "entityType":   "cast_member",
                        "entityId":     c.id,
                        "message":      message,
                    }
                )
                signals_created += 1

    # Auto-resolve signals for cast no longer above threshold
    for cid, sig in existing_by_cast.items():
        if cid not in signaled_ids:
            await prisma.productionsignal.update(
                where={"id": sig.id},
                data={
                    "resolved": True,
                    "resolvedAt": datetime.now(timezone.utc),
                    "resolvedBy": "crew_engine",
                },
            )
            signals_resolved += 1

    return DoodResponse(
        production_id=production_id,
        production_title=production.title,
        total_shoot_days=len(shoot_days),
        cast_count=len(cast_rows),
        cast_with_scenes=len(cast_out),
        total_work_days=total_work,
        total_hold_days=total_holds,
        total_hold_cost=round(total_hold_cost, 2),
        min_possible_hold_days=min_total_holds,
        reorder_savings_opportunity=round(total_hold_cost, 2),
        signals_created=signals_created,
        signals_resolved=signals_resolved,
        cast=cast_out,
    )
