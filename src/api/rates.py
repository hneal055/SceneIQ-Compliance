"""
Rates Engine API — union and non-union crew cost rates by guild, department, and market.
Adapted from SceneIQ budget-app rates engine.
"""
import json
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Query
from pydantic import BaseModel

router = APIRouter(prefix="/rates", tags=["Rates Engine"])

_DATA = Path(__file__).parent.parent / "data"
UNION_RATES: dict = json.loads((_DATA / "union_rates" / "union_rates.json").read_text(encoding="utf-8"))
NON_UNION_RATES: dict = json.loads((_DATA / "nonunion_rates" / "nonunion_rates.json").read_text(encoding="utf-8"))


class RateRequest(BaseModel):
    guild: str
    category: str
    budget_tier: Optional[str] = "basic"
    location: Optional[str] = None
    shoot_days: Optional[int] = None
    shoot_weeks: Optional[int] = None


@router.get("/union", summary="Get all union rates by guild")
async def get_union_rates(guild: Optional[str] = Query(None)):
    if guild:
        for key in UNION_RATES:
            if key.upper() == guild.upper():
                return {"guild": key, "rates": UNION_RATES[key]}
        return {"error": f"Guild {guild} not found", "available": list(UNION_RATES.keys())}
    return {"unions": UNION_RATES}


@router.get("/nonunion", summary="Get non-union rates by market")
async def get_nonunion_rates(location: Optional[str] = Query(None)):
    if location:
        loc = location.lower().replace(" ", "_").replace("-", "_")
        if loc in NON_UNION_RATES:
            return {"location": location, "rates": NON_UNION_RATES[loc]}
        return {"error": f"Location {location} not found", "available": list(NON_UNION_RATES.keys())}
    return {"markets": NON_UNION_RATES}


@router.post("/estimate", summary="Estimate crew costs for a production")
async def estimate_crew_costs(request: RateRequest):
    results = {}
    weeks = request.shoot_weeks or (request.shoot_days / 5 if request.shoot_days else 4)
    guild = request.guild.upper()

    if guild == "IATSE" and request.category in UNION_RATES.get("IATSE", {}):
        dept = UNION_RATES["IATSE"][request.category]
        for role, rate in dept.items():
            if "weekly" in role and isinstance(rate, (int, float)):
                results[role] = round(rate * weeks)
    elif guild == "SAG-AFTRA":
        tier = request.budget_tier or "basic"
        if tier in UNION_RATES.get("SAG-AFTRA", {}):
            results = UNION_RATES["SAG-AFTRA"][tier]
    elif guild == "DGA":
        if request.category in UNION_RATES.get("DGA", {}):
            results = UNION_RATES["DGA"][request.category]
    elif guild == "TEAMSTERS":
        if request.category in UNION_RATES.get("Teamsters", {}):
            dept = UNION_RATES["Teamsters"][request.category]
            for role, rate in dept.items():
                if "weekly" in role and isinstance(rate, (int, float)):
                    results[role] = round(rate * weeks)
    elif guild == "WGA":
        if request.category in UNION_RATES.get("WGA", {}):
            results = UNION_RATES["WGA"][request.category]

    return {
        "guild": request.guild,
        "category": request.category,
        "budget_tier": request.budget_tier,
        "shoot_weeks": round(weeks, 1),
        "estimated_costs": results,
    }


@router.get("/guilds", summary="List all available guilds and unions")
async def list_guilds():
    return {
        "guilds": list(UNION_RATES.keys()),
        "nonunion_markets": list(NON_UNION_RATES.keys()),
    }
