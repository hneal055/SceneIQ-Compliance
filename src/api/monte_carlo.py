"""
monte_carlo.py - Phase 6 Slice 5: Monte Carlo Completion-Cost Engine
GET /productions/{id}/budget/monte-carlo?runs=5000

Simulates the production's completion cost by sampling from the
platform's OWN verified risk findings rather than generic variance:
each priced exposure (OT projection, turnaround forced-call risk,
meal penalties, DOOD hold waste, weather cover days) is sampled for
occurrence (probability mapped from the associated day's schedule
risk tier) and magnitude (triangular around the priced figure), on
top of baseline execution variance. Reports P10/P50/P90, probability
of exceeding budget and budget+contingency, writes the distribution
to the Prediction table as a gradeable forecast, and fires an
overrun_risk signal when P(over budget + contingency) is material.

Successor to EnhancedBudgetPro's MonteCarloBudgetEngine (uniform
+/-volatility on one base cost); this engine's variance is sourced
from audited findings, not guesses.
"""
import json
import logging
import random
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel
from datetime import datetime, timezone

from src.utils.database import prisma
from src.api.ot_prediction import predict_ot
from src.api.turnaround_analysis import analyze_turnaround
from src.api.meal_penalty import analyze_meal_penalties
from src.api.dood_analysis import analyze_dood
from src.api.fringe_analysis import analyze_fringes

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Production Brain"])

# Baseline execution variance (sigma as fraction of budget) - covers the
# thousand small overages no engine models individually
_BASELINE_SIGMA = 0.03
# Contingency fraction for the second threshold
_CONTINGENCY = 0.10
# Occurrence probability by schedule-risk tier of the associated exposure
_P_OCCUR = {"critical": 0.70, "high": 0.50, "moderate": 0.30, "low": 0.15, "default": 0.50}
# Triangular magnitude bounds as multiples of the priced exposure
_TRI_LOW, _TRI_MODE, _TRI_HIGH = 0.25, 1.0, 1.75
# Signal thresholds on P(over budget + contingency)
_SIGNAL_MEDIUM = 0.10
_SIGNAL_HIGH = 0.30

_MIN_RUNS, _MAX_RUNS, _DEFAULT_RUNS = 1000, 20000, 5000


class ExposureInput(BaseModel):
    name: str
    priced_amount: float
    occurrence_probability: float
    source_engine: str


class MonteCarloResponse(BaseModel):
    production_id: str
    production_title: str
    runs: int
    budget_total: float
    contingency_pct: float
    exposures: List[ExposureInput]
    baseline_sigma_pct: float
    mean_completion: float
    p10: float
    p50: float
    p90: float
    prob_over_budget: float
    prob_over_budget_plus_contingency: float
    expected_overage: float
    signal_created: bool
    prediction_id: Optional[str]


def _percentile(sorted_vals, q):
    idx = min(len(sorted_vals) - 1, max(0, int(len(sorted_vals) * q)))
    return sorted_vals[idx]


@router.get(
    "/productions/{production_id}/budget/monte-carlo",
    response_model=MonteCarloResponse,
    summary="Completion-cost simulation sampling from the platform's own risk findings",
)
async def simulate_completion(
    production_id: str,
    runs: int = Query(_DEFAULT_RUNS, ge=_MIN_RUNS, le=_MAX_RUNS),
):
    production = await prisma.production.find_unique(where={"id": production_id})
    if not production:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Production not found")
    budget_total = production.budgetTotal or 0.0
    if budget_total <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Production has no budgetTotal set")

    # ---- Gather exposures from the platform's own engines --------------
    # (idempotent: each engine dedupes/updates its own signals)
    exposures: List[ExposureInput] = []

    # Schedule risk tiers per day, for occurrence probabilities
    day_tier: dict = {}
    try:
        from src.api.schedule_risk import score_schedule
        sr = await score_schedule(production_id)
        for d in sr.days:
            day_tier[d.day_number] = d.tier
    except Exception as exc:
        logger.warning("Schedule risk unavailable for occurrence mapping: %s", exc)

    def tier_prob(day_numbers):
        tiers = [day_tier.get(n) for n in day_numbers if day_tier.get(n)]
        if not tiers:
            return _P_OCCUR["default"]
        worst = max(tiers, key=lambda t: _P_OCCUR.get(t, 0))
        return _P_OCCUR.get(worst, _P_OCCUR["default"])

    try:
        ot = await predict_ot(production_id)
        if ot.projected_ot_cost > 0:
            risk_days = [d.day_number for d in ot.shoot_days if d.ot_risk != "none"]
            exposures.append(ExposureInput(
                name="overtime", priced_amount=round(ot.projected_ot_cost, 2),
                occurrence_probability=tier_prob(risk_days),
                source_engine="ot_prediction"))
    except Exception as exc:
        logger.warning("OT engine unavailable: %s", exc)

    try:
        ta = await analyze_turnaround(production_id)
        if ta.total_forced_call_exposure > 0:
            v_days = [p.to_day for p in ta.pairs if p.violation]
            exposures.append(ExposureInput(
                name="turnaround_forced_calls",
                priced_amount=round(ta.total_forced_call_exposure, 2),
                occurrence_probability=tier_prob(v_days),
                source_engine="turnaround_analysis"))
    except Exception as exc:
        logger.warning("Turnaround engine unavailable: %s", exc)

    try:
        mp = await analyze_meal_penalties(production_id)
        if mp.total_estimated_exposure > 0:
            p_days = [d.day_number for d in mp.days if d.risk == "penalty"]
            exposures.append(ExposureInput(
                name="meal_penalties",
                priced_amount=round(mp.total_estimated_exposure, 2),
                occurrence_probability=tier_prob(p_days),
                source_engine="meal_penalty"))
    except Exception as exc:
        logger.warning("Meal penalty engine unavailable: %s", exc)

    try:
        dd = await analyze_dood(production_id)
        if dd.total_hold_cost > 0:
            # Holds are near-certain unless the schedule is reordered
            exposures.append(ExposureInput(
                name="cast_hold_days", priced_amount=round(dd.total_hold_cost, 2),
                occurrence_probability=0.85,
                source_engine="dood_analysis"))
    except Exception as exc:
        logger.warning("DOOD engine unavailable: %s", exc)

    try:
        from src.api.weather_risk import analyze_weather
        wx = await analyze_weather(production_id)
        if wx.risk_days > 0:
            fr = await analyze_fringes(production_id)
            cover_day_cost = fr.loaded_labor_daily
            exposures.append(ExposureInput(
                name="weather_cover_days",
                priced_amount=round(wx.risk_days * cover_day_cost, 2),
                occurrence_probability=0.5,
                source_engine="weather_risk"))
    except Exception as exc:
        logger.warning("Weather engine unavailable: %s", exc)

    # ---- Simulate --------------------------------------------------------
    rng = random.Random()  # nondeterministic; seed param could be added later
    sigma = budget_total * _BASELINE_SIGMA
    results = []
    for _ in range(runs):
        total = budget_total + rng.gauss(0, sigma)
        for ex in exposures:
            if rng.random() < ex.occurrence_probability:
                total += rng.triangular(
                    ex.priced_amount * _TRI_LOW,
                    ex.priced_amount * _TRI_HIGH,
                    ex.priced_amount * _TRI_MODE,
                )
        results.append(total)
    results.sort()

    mean_completion = sum(results) / len(results)
    p10 = _percentile(results, 0.10)
    p50 = _percentile(results, 0.50)
    p90 = _percentile(results, 0.90)
    over_budget = sum(1 for r in results if r > budget_total) / runs
    threshold = budget_total * (1 + _CONTINGENCY)
    over_contingency = sum(1 for r in results if r > threshold) / runs
    expected_overage = mean_completion - budget_total

    # ---- Prediction row (upsert) ------------------------------------------
    payload = {
        "forecast": "completion_cost_distribution",
        "runs": runs,
        "budget_total": budget_total,
        "exposures": [e.dict() for e in exposures],
        "p10": round(p10, 2), "p50": round(p50, 2), "p90": round(p90, 2),
        "mean": round(mean_completion, 2),
        "prob_over_budget": round(over_budget, 3),
        "prob_over_budget_plus_contingency": round(over_contingency, 3),
        "gradeable_claim": (
            f"Final completion cost will land between ${p10:,.0f} (P10) and "
            f"${p90:,.0f} (P90)."
        ),
    }
    narrative = (
        f"Completion-cost simulation ({runs:,} runs) from {len(exposures)} audited "
        f"exposures: P50 ${p50:,.0f}, P90 ${p90:,.0f}. "
        f"P(over ${budget_total:,.0f} budget) = {over_budget*100:.0f}%; "
        f"P(over budget + {_CONTINGENCY*100:.0f}% contingency) = "
        f"{over_contingency*100:.1f}%. Expected overage ${expected_overage:,.0f}."
    )
    existing = await prisma.prediction.find_many(where={
        "productionId": production_id, "source": "monte_carlo_engine",
        "kind": "forecast", "status": "proposed",
    })
    if existing:
        row = await prisma.prediction.update(
            where={"id": existing[0].id},
            data={"payload": json.dumps(payload), "narrative": narrative})
    else:
        row = await prisma.prediction.create(data={
            "productionId": production_id, "source": "monte_carlo_engine",
            "kind": "forecast", "entityType": "production",
            "entityId": production_id,
            "payload": json.dumps(payload), "narrative": narrative,
        })

    # ---- overrun_risk signal ------------------------------------------------
    signal_created = False
    sig_existing = await prisma.productionsignal.find_many(where={
        "productionId": production_id, "signalType": "overrun_risk",
        "source": "monte_carlo_engine", "resolved": False,
    })
    if over_contingency >= _SIGNAL_MEDIUM:
        severity = "high" if over_contingency >= _SIGNAL_HIGH else "medium"
        message = (
            f"Budget overrun risk: {over_contingency*100:.0f}% probability of "
            f"exceeding budget plus {_CONTINGENCY*100:.0f}% contingency "
            f"(P90 completion ${p90:,.0f} vs ${budget_total:,.0f} budget). "
            f"Largest exposures: "
            + ", ".join(f"{e.name} ${e.priced_amount:,.0f}"
                        for e in sorted(exposures, key=lambda x: -x.priced_amount)[:3])
            + "."
        )
        if sig_existing:
            await prisma.productionsignal.update(
                where={"id": sig_existing[0].id},
                data={"severity": severity, "message": message})
        else:
            await prisma.productionsignal.create(data={
                "productionId": production_id, "signalType": "overrun_risk",
                "severity": severity, "source": "monte_carlo_engine",
                "entityType": "production", "entityId": production_id,
                "message": message,
            })
            signal_created = True
    else:
        if sig_existing:
            await prisma.productionsignal.update(
                where={"id": sig_existing[0].id},
                data={"resolved": True,
                      "resolvedAt": datetime.now(timezone.utc),
                      "resolvedBy": "monte_carlo_engine"})

    return MonteCarloResponse(
        production_id=production_id,
        production_title=production.title,
        runs=runs,
        budget_total=budget_total,
        contingency_pct=_CONTINGENCY * 100,
        exposures=exposures,
        baseline_sigma_pct=_BASELINE_SIGMA * 100,
        mean_completion=round(mean_completion, 2),
        p10=round(p10, 2), p50=round(p50, 2), p90=round(p90, 2),
        prob_over_budget=round(over_budget, 3),
        prob_over_budget_plus_contingency=round(over_contingency, 3),
        expected_overage=round(expected_overage, 2),
        signal_created=signal_created,
        prediction_id=row.id,
    )
