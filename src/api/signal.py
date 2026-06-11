"""
Production Signals API
Autonomous OS intelligence layer â€” any agent writes signals here,
any dashboard reads them.

Endpoints:
  POST   /productions/{production_id}/signals        â€” create a signal
  GET    /productions/{production_id}/signals        â€” list signals for a production
  GET    /productions/{production_id}/signals/active â€” unresolved signals only
  PATCH  /productions/{production_id}/signals/{id}/resolve â€” mark resolved
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from prisma import Prisma

router = APIRouter(
    prefix="/productions",
    tags=["Production Signals"]
)


# â”€â”€â”€ Request / Response Models â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class SignalCreate(BaseModel):
    signalType: str
    # budget_drift / ot_spike / weather_risk / schedule_slip
    # vfx_inflation / crew_conflict / location_issue
    severity: str
    # low / medium / high / critical
    source: Optional[str] = "manual"
    # aura / compliance / budget / manual
    entityType: Optional[str] = None
    # scene / crew / location / budget_line
    entityId: Optional[str] = None
    message: str


class SignalResolve(BaseModel):
    resolvedBy: Optional[str] = "user"


class SignalResponse(BaseModel):
    id: str
    productionId: str
    signalType: str
    severity: str
    source: Optional[str]
    entityType: Optional[str]
    entityId: Optional[str]
    message: str
    resolved: bool
    resolvedAt: Optional[datetime]
    resolvedBy: Optional[str]
    createdAt: datetime
    updatedAt: datetime


# â”€â”€â”€ Endpoints â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@router.post("/{production_id}/signals", response_model=SignalResponse)
async def create_signal(production_id: str, data: SignalCreate):
    """
    Write a signal to a production.
    Called by any agent: AURA, budget engine, compliance checker, or manual.
    """
    db = Prisma()
    await db.connect()
    try:
        # Verify production exists
        production = await db.production.find_unique(
            where={"id": production_id}
        )
        if not production:
            raise HTTPException(status_code=404, detail="Production not found")

        signal = await db.productionsignal.create(
            data={
                "productionId": production_id,
                "signalType":   data.signalType,
                "severity":     data.severity,
                "source":       data.source,
                "entityType":   data.entityType,
                "entityId":     data.entityId,
                "message":      data.message,
            }
        )
        return signal
    finally:
        await db.disconnect()


@router.get("/{production_id}/signals", response_model=List[SignalResponse])
async def list_signals(production_id: str):
    """
    All signals for a production, newest first.
    """
    db = Prisma()
    await db.connect()
    try:
        signals = await db.productionsignal.find_many(
            where={"productionId": production_id},
            order={"createdAt": "desc"}
        )
        return signals
    finally:
        await db.disconnect()


@router.get("/{production_id}/signals/active", response_model=List[SignalResponse])
async def active_signals(production_id: str):
    """
    Unresolved signals only â€” what the autonomous OS dashboard shows.
    Ordered by severity: critical â†’ high â†’ medium â†’ low.
    """
    db = Prisma()
    await db.connect()
    try:
        signals = await db.productionsignal.find_many(
            where={
                "productionId": production_id,
                "resolved": False
            },
            order={"createdAt": "desc"}
        )

        # Sort by severity weight
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        signals.sort(key=lambda s: severity_order.get(s.severity, 99))

        return signals
    finally:
        await db.disconnect()


@router.patch("/{production_id}/signals/{signal_id}/resolve", response_model=SignalResponse)
async def resolve_signal(production_id: str, signal_id: str, data: SignalResolve):
    """
    Mark a signal as resolved.
    Called when a human or agent acknowledges and addresses the issue.
    """
    db = Prisma()
    await db.connect()
    try:
        signal = await db.productionsignal.find_unique(
            where={"id": signal_id}
        )
        if not signal:
            raise HTTPException(status_code=404, detail="Signal not found")
        if signal.productionId != production_id:
            raise HTTPException(status_code=403, detail="Signal does not belong to this production")

        updated = await db.productionsignal.update(
            where={"id": signal_id},
            data={
                "resolved":    True,
                "resolvedAt":  datetime.utcnow(),
                "resolvedBy":  data.resolvedBy,
            }
        )
        return updated
    finally:
        await db.disconnect()

