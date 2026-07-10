"""
Production Signals API
Autonomous OS intelligence layer — any agent writes signals here,
any dashboard reads them.

Endpoints:
  POST   /productions/{production_id}/signals        — create a signal
  GET    /productions/{production_id}/signals        — list signals for a production
  GET    /productions/{production_id}/signals/active — unresolved signals only
  PATCH  /productions/{production_id}/signals/{id}/resolve — mark resolved
"""
import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

from src.utils.database import prisma

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/productions",
    tags=["Production Signals"]
)


class SignalCreate(BaseModel):
    signalType: str
    severity: str
    source: Optional[str] = "manual"
    entityType: Optional[str] = None
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


@router.post("/{production_id}/signals", response_model=SignalResponse)
async def create_signal(production_id: str, data: SignalCreate):
    """Write a signal to a production. Called by any agent or manually."""
    production = await prisma.production.find_unique(where={"id": production_id})
    if not production:
        raise HTTPException(status_code=404, detail="Production not found")

    signal = await prisma.productionsignal.create(
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


@router.get("/{production_id}/signals", response_model=List[SignalResponse])
async def list_signals(production_id: str):
    """All signals for a production, newest first."""
    signals = await prisma.productionsignal.find_many(
        where={"productionId": production_id},
        order={"createdAt": "desc"}
    )
    return signals


@router.get("/{production_id}/signals/active", response_model=List[SignalResponse])
async def active_signals(production_id: str):
    """Unresolved signals only — what the Signal Dashboard shows."""
    signals = await prisma.productionsignal.find_many(
        where={
            "productionId": production_id,
            "resolved": False,
        },
        order={"createdAt": "desc"}
    )
    severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    signals.sort(key=lambda s: severity_order.get(s.severity, 99))
    return signals


@router.patch("/{production_id}/signals/{signal_id}/resolve", response_model=SignalResponse)
async def resolve_signal(production_id: str, signal_id: str, data: SignalResolve):
    """Mark a signal as resolved."""
    signal = await prisma.productionsignal.find_unique(where={"id": signal_id})
    if not signal:
        raise HTTPException(status_code=404, detail="Signal not found")
    if signal.productionId != production_id:
        raise HTTPException(status_code=403, detail="Signal does not belong to this production")

    updated = await prisma.productionsignal.update(
        where={"id": signal_id},
        data={
            "resolved":   True,
            "resolvedAt": datetime.utcnow(),
            "resolvedBy": data.resolvedBy,
        }
    )
    return updated
