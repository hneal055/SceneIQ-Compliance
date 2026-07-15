"""
brain.py - Phase 6 Slices 1+2: Predictive Production Brain (Synthesis + Closed Loop)

POST /productions/{id}/brain/run
    Fires signal synthesis: groups unresolved signals into clusters
    (consecutive shoot days, cast, production-level), diagnoses each
    cluster's root cause, generates concrete recommendations (some
    machine-applicable), and writes every diagnosis and recommendation
    to the Prediction table as falsifiable records. Narrative is
    template-generated, optionally enhanced by one Claude call.

POST /productions/{id}/brain/predictions/{prediction_id}/apply
    Human-in-the-loop execution of ONE action type: move_scene. Moves
    the scene, recomputes affected day page totals, re-runs the OT and
    DOOD engines so their signals auto-resolve, and marks the
    prediction applied. Never runs without this explicit call.

POST /productions/{id}/brain/predictions/{prediction_id}/dismiss
    Marks a recommendation dismissed. Dismissals are data.

GET /productions/{id}/brain/predictions
    Lists prediction records for the production.
"""
import json
import logging
import os
from typing import List, Optional
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from datetime import datetime, timezone

from src.utils.database import prisma

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Production Brain"])

_STANDARD_PAGES = 8.0


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------

class PredictionOut(BaseModel):
    id: str
    kind: str
    source: str
    entity_type: Optional[str]
    entity_id: Optional[str]
    status: str
    narrative: Optional[str]
    payload: dict


class BrainRunResponse(BaseModel):
    production_id: str
    production_title: str
    unresolved_signals: int
    clusters: int
    diagnoses_created: int
    recommendations_created: int
    narrative_source: str
    predictions: List[PredictionOut]


class ApplyResponse(BaseModel):
    prediction_id: str
    action: str
    detail: str
    engines_rerun: List[str]
    signals_resolved: int
    prediction_status: str


# ---------------------------------------------------------------------------
# Narrative generation: template first, Claude enhancement if available
# ---------------------------------------------------------------------------

async def _claude_narrative(prompt: str) -> Optional[str]:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return None
    try:
        import anthropic
        client = anthropic.AsyncAnthropic(api_key=api_key)
        msg = await client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=400,
            messages=[{"role": "user", "content": prompt}],
        )
        parts = [b.text for b in msg.content if getattr(b, "type", "") == "text"]
        text = "\n".join(parts).strip()
        return text or None
    except Exception as exc:  # credits, network, missing package - degrade gracefully
        logger.warning("Claude narrative unavailable: %s", exc)
        return None


# ---------------------------------------------------------------------------
# Brain run
# ---------------------------------------------------------------------------

@router.get("/brain/diag", summary="TEMPORARY: diagnose Claude connectivity")
async def brain_diag():
    import os
    out = {
        "key_present": bool(os.environ.get("ANTHROPIC_API_KEY")),
        "key_prefix": (os.environ.get("ANTHROPIC_API_KEY") or "")[:14],
        "base_url_env": os.environ.get("ANTHROPIC_BASE_URL", "not set"),
        "proxy_vars": [k for k in os.environ if "PROXY" in k.upper()] or "none",
    }
    try:
        import anthropic
        out["anthropic_version"] = anthropic.__version__
        client = anthropic.AsyncAnthropic()
        msg = await client.messages.create(
            model="claude-sonnet-4-6", max_tokens=20,
            messages=[{"role": "user", "content": "Say OK"}],
        )
        out["call"] = "SUCCEEDED: " + msg.content[0].text
    except Exception as e:
        chain = []
        cur = e
        while cur is not None:
            chain.append(f"{type(cur).__name__}: {cur}")
            cur = cur.__cause__ or cur.__context__
            if len(chain) > 6:
                break
        out["call"] = "FAILED"
        out["cause_chain"] = chain
    # Raw probes to separate DNS / TLS / egress
    import httpx
    for name, url in [("https_anthropic", "https://api.anthropic.com"),
                      ("https_google", "https://www.google.com")]:
        try:
            r = httpx.get(url, timeout=8)
            out[name] = f"OK {r.status_code}"
        except Exception as pe:
            root = pe
            while root.__cause__ or root.__context__:
                root = root.__cause__ or root.__context__
            out[name] = f"FAIL {type(pe).__name__} / root: {type(root).__name__}: {root}"
    return out


@router.post(
    "/productions/{production_id}/brain/run",
    response_model=BrainRunResponse,
    summary="Run signal synthesis: cluster, diagnose, recommend, record",
)
async def run_brain(production_id: str):
    production = await prisma.production.find_unique(where={"id": production_id})
    if not production:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Production not found")

    signals = await prisma.productionsignal.find_many(
        where={"productionId": production_id, "resolved": False},
    )
    shoot_days = await prisma.shootday.find_many(
        where={"productionId": production_id}, order={"dayNumber": "asc"},
    )
    scenes = await prisma.scene.find_many(where={"productionId": production_id})
    cast_rows = await prisma.castmember.find_many(where={"productionId": production_id})

    day_by_id = {d.id: d for d in shoot_days}
    cast_by_id = {c.id: c for c in cast_rows}
    scenes_by_day: dict = {}
    for s in scenes:
        if s.shootDayId:
            scenes_by_day.setdefault(s.shootDayId, []).append(s)

    def day_pages(day_id: str) -> float:
        d = day_by_id.get(day_id)
        if d and d.totalPages and d.totalPages > 0:
            return d.totalPages
        return sum(s.pageCount or 0 for s in scenes_by_day.get(day_id, []))

    # --- Clustering -------------------------------------------------------
    day_signals: dict = {}
    cast_signals = []
    prod_signals = []
    for sig in signals:
        if sig.entityType == "shoot_day" and sig.entityId in day_by_id:
            day_signals.setdefault(day_by_id[sig.entityId].dayNumber, []).append(sig)
        elif sig.entityType == "cast_member":
            cast_signals.append(sig)
        else:
            prod_signals.append(sig)

    # Merge consecutive day numbers into clusters
    day_clusters = []
    for n in sorted(day_signals):
        if day_clusters and n == day_clusters[-1]["days"][-1] + 1:
            day_clusters[-1]["days"].append(n)
            day_clusters[-1]["signals"].extend(day_signals[n])
        else:
            day_clusters.append({"days": [n], "signals": list(day_signals[n])})

    predictions_created: List[PredictionOut] = []
    diagnoses = 0
    recommendations = 0

    async def record(kind, payload, narrative, entity_type=None, entity_id=None):
        row = await prisma.prediction.create(data={
            "productionId": production_id,
            "source": "brain",
            "kind": kind,
            "entityType": entity_type,
            "entityId": entity_id,
            "payload": json.dumps(payload),
            "narrative": narrative,
        })
        predictions_created.append(PredictionOut(
            id=row.id, kind=kind, source="brain",
            entity_type=entity_type, entity_id=entity_id,
            status="proposed", narrative=narrative, payload=payload,
        ))
        return row

    # --- Day clusters: diagnose and recommend ------------------------------
    for cluster in day_clusters:
        days = cluster["days"]
        sigs = cluster["signals"]
        types = sorted({s.signalType for s in sigs})
        day_label = f"Day {days[0]}" if len(days) == 1 else f"Days {days[0]}-{days[-1]}"

        diag_payload = {
            "cluster": "shoot_days", "days": days,
            "signal_types": types, "signal_count": len(sigs),
            "root_cause": None,
        }

        root_bits = []
        if "ot_spike" in types:
            root_bits.append("scheduled page count exceeds the 8-page standard")
        if "turnaround_violation" in types:
            root_bits.append("the late wrap invades the next day's rest period")
        if "meal_penalty" in types:
            root_bits.append("the working span runs past the second-meal deadline")
        if "crew_coverage_gap" in types:
            root_bits.append("required departments are missing from the roster")
        diag_payload["root_cause"] = (
            f"{day_label} is overloaded: " + "; ".join(root_bits)
            if root_bits else f"{day_label} has {len(sigs)} unresolved signals"
        )
        diag = await record("diagnosis", diag_payload, diag_payload["root_cause"],
                            "shoot_day_cluster", None)
        diagnoses += 1

        # Recommendations: move heavy scenes from overloaded days to light days
        if "ot_spike" in types:
            for n in days:
                day = next((d for d in shoot_days if d.dayNumber == n), None)
                if not day:
                    continue
                pages = day_pages(day.id)
                if pages <= _STANDARD_PAGES:
                    continue
                candidates = sorted(
                    scenes_by_day.get(day.id, []),
                    key=lambda s: (
                        0 if (s.notes and "multiple days" in s.notes.lower()) else 1,
                        -(s.pageCount or 0),
                    ),
                )
                targets = sorted(
                    (d for d in shoot_days if d.id != day.id),
                    key=lambda d: day_pages(d.id),
                )
                made = 0
                for sc in candidates:
                    if made >= 2 or pages <= _STANDARD_PAGES:
                        break
                    sc_pages = sc.pageCount or 0
                    if sc_pages <= 0:
                        continue
                    target = next(
                        (t for t in targets
                         if day_pages(t.id) + sc_pages <= _STANDARD_PAGES),
                        None,
                    )
                    if not target:
                        continue
                    # Synergy: does this move place a held actor onto a hold day?
                    synergy = []
                    for cid in (sc.castIds or []):
                        c = cast_by_id.get(cid)
                        if c:
                            synergy.append(c.characterName)
                    rec_payload = {
                        "action": "move_scene",
                        "scene_id": sc.id,
                        "scene_number": sc.sceneNumber,
                        "scene_title": sc.title,
                        "pages": sc_pages,
                        "from_day_id": day.id, "from_day": day.dayNumber,
                        "to_day_id": target.id, "to_day": target.dayNumber,
                        "expected": [
                            f"Day {day.dayNumber} drops from {pages:.2f} to "
                            f"{pages - sc_pages:.2f} pages",
                            f"Day {target.dayNumber} rises to "
                            f"{day_pages(target.id) + sc_pages:.2f} pages",
                        ],
                        "cast_affected": synergy,
                        "diagnosis_id": diag.id,
                    }
                    narrative = (
                        f"Move scene {sc.sceneNumber} '{sc.title}' "
                        f"({sc_pages:.2f} pages) from Day {day.dayNumber} to "
                        f"Day {target.dayNumber}. "
                        + " ".join(rec_payload["expected"])
                        + (f" Scene involves {', '.join(synergy)} - check DOOD "
                           f"holds for knock-on savings." if synergy else "")
                    )
                    await record("recommendation", rec_payload, narrative,
                                 "scene", sc.id)
                    recommendations += 1
                    made += 1
                    pages -= sc_pages

        if "crew_coverage_gap" in types:
            missing = []
            for s in sigs:
                if s.signalType == "crew_coverage_gap" and s.message:
                    missing.append(s.message.split("missing ")[-1].split(".")[0]
                                   if "missing " in s.message else "required departments")
            rec_payload = {
                "action": "hire",
                "days": days,
                "detail": f"Hire or day-play coverage for: {'; '.join(missing)}",
                "machine_applicable": False,
                "diagnosis_id": diag.id,
            }
            await record("recommendation", rec_payload, rec_payload["detail"],
                         "shoot_day_cluster", None)
            recommendations += 1

        if "turnaround_violation" in types or "meal_penalty" in types:
            rec_payload = {
                "action": "adjust_times",
                "days": days,
                "detail": (f"Revisit call/wrap times across {day_label}: an earlier "
                           f"wrap or later next-day call restores the 10-hour "
                           f"turnaround and shortens the meal-penalty span. "
                           f"Moving pages off the overloaded day makes the earlier "
                           f"wrap achievable."),
                "machine_applicable": False,
                "diagnosis_id": diag.id,
            }
            await record("recommendation", rec_payload, rec_payload["detail"],
                         "shoot_day_cluster", None)
            recommendations += 1

    # --- Cast cluster -------------------------------------------------------
    if cast_signals:
        held = []
        for s in cast_signals:
            c = cast_by_id.get(s.entityId)
            held.append(c.characterName if c else s.entityId)
        payload = {
            "cluster": "cast_holds",
            "actors": held,
            "signal_count": len(cast_signals),
            "root_cause": ("Scene-to-day ordering leaves actors held between "
                           "work days; clustering each actor's scenes removes "
                           "paid idle days."),
        }
        narrative = (f"Hold-day waste across {', '.join(held)}: reorder or move "
                     f"scenes to cluster each actor's work days. Any move_scene "
                     f"recommendation that places a held actor's scene onto one "
                     f"of their hold days eliminates that hold directly.")
        await record("diagnosis", payload, narrative, "cast_cluster", None)
        diagnoses += 1

    # --- Production-level ----------------------------------------------------
    for s in prod_signals:
        payload = {
            "cluster": "production",
            "signal_type": s.signalType,
            "root_cause": s.message,
        }
        await record("diagnosis", payload,
                     f"Production-level: {s.message}", "production", production_id)
        diagnoses += 1

    # --- Narrative enhancement (one Claude call, graceful fallback) ----------
    narrative_source = "template"
    if predictions_created:
        summary_lines = [p.narrative for p in predictions_created if p.narrative]
        prompt = (
            "You are the Production Brain for an indie film platform. In under "
            "150 words, write a producer-facing executive summary of these "
            "findings for the production '" + production.title + "'. Lead with "
            "the single highest-value action. Findings:\n- "
            + "\n- ".join(summary_lines[:10])
        )
        enhanced = await _claude_narrative(prompt)
        if enhanced:
            narrative_source = "claude"
            await record("diagnosis",
                         {"cluster": "executive_summary"},
                         enhanced, "production", production_id)
            diagnoses += 1

    return BrainRunResponse(
        production_id=production_id,
        production_title=production.title,
        unresolved_signals=len(signals),
        clusters=len(day_clusters) + (1 if cast_signals else 0) + len(prod_signals),
        diagnoses_created=diagnoses,
        recommendations_created=recommendations,
        narrative_source=narrative_source,
        predictions=predictions_created,
    )


# ---------------------------------------------------------------------------
# Human-in-the-loop: apply / dismiss
# ---------------------------------------------------------------------------

@router.post(
    "/productions/{production_id}/brain/predictions/{prediction_id}/apply",
    response_model=ApplyResponse,
    summary="Apply a machine-applicable recommendation (human-approved)",
)
async def apply_prediction(production_id: str, prediction_id: str):
    pred = await prisma.prediction.find_unique(where={"id": prediction_id})
    if not pred or pred.productionId != production_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prediction not found")
    if pred.status != "proposed":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                            detail=f"Prediction is '{pred.status}', not proposed")

    payload = pred.payload if isinstance(pred.payload, dict) else json.loads(pred.payload)
    action = payload.get("action")
    if action != "move_scene":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Action '{action}' is not machine-applicable; handle manually "
                   f"and dismiss or grade this prediction.",
        )

    scene = await prisma.scene.find_unique(where={"id": payload["scene_id"]})
    if not scene:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scene not found")

    from_day_id = payload["from_day_id"]
    to_day_id = payload["to_day_id"]

    # Move the scene
    await prisma.scene.update(where={"id": scene.id}, data={"shootDayId": to_day_id})

    # Recompute totalPages on both affected days from their scenes
    for did in (from_day_id, to_day_id):
        day_scenes = await prisma.scene.find_many(
            where={"productionId": production_id, "shootDayId": did}
        )
        total = sum(s.pageCount or 0 for s in day_scenes)
        await prisma.shootday.update(where={"id": did}, data={"totalPages": total})

    # Closed loop: re-run the engines whose inputs changed
    from src.api.ot_prediction import predict_ot
    from src.api.dood_analysis import analyze_dood
    ot = await predict_ot(production_id)
    dood = await analyze_dood(production_id)
    resolved = getattr(dood, "signals_resolved", 0)
    # OT resolves per-day signals internally; count via a fresh signal read
    still_open = await prisma.productionsignal.count(
        where={"productionId": production_id, "resolved": False}
    )

    await prisma.prediction.update(
        where={"id": prediction_id},
        data={"status": "applied", "resolvedAt": datetime.now(timezone.utc)},
    )

    return ApplyResponse(
        prediction_id=prediction_id,
        action=action,
        detail=(f"Scene {payload.get('scene_number')} moved Day "
                f"{payload.get('from_day')} -> Day {payload.get('to_day')}; "
                f"day page totals recomputed; {still_open} signals remain open."),
        engines_rerun=["ot_prediction", "dood_analysis"],
        signals_resolved=resolved,
        prediction_status="applied",
    )


@router.post(
    "/productions/{production_id}/brain/predictions/{prediction_id}/dismiss",
    summary="Dismiss a recommendation (dismissals are data)",
)
async def dismiss_prediction(production_id: str, prediction_id: str):
    pred = await prisma.prediction.find_unique(where={"id": prediction_id})
    if not pred or pred.productionId != production_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prediction not found")
    if pred.status != "proposed":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                            detail=f"Prediction is '{pred.status}', not proposed")
    await prisma.prediction.update(
        where={"id": prediction_id},
        data={"status": "dismissed", "resolvedAt": datetime.now(timezone.utc)},
    )
    return {"prediction_id": prediction_id, "status": "dismissed"}


@router.get(
    "/productions/{production_id}/brain/predictions",
    summary="List prediction records",
)
async def list_predictions(production_id: str, status_filter: Optional[str] = None):
    where = {"productionId": production_id}
    if status_filter:
        where["status"] = status_filter
    rows = await prisma.prediction.find_many(where=where, order={"createdAt": "desc"})
    out = []
    for r in rows:
        payload = r.payload if isinstance(r.payload, dict) else json.loads(r.payload)
        out.append({
            "id": r.id, "kind": r.kind, "source": r.source,
            "status": r.status, "narrative": r.narrative,
            "payload": payload, "created_at": str(r.createdAt),
        })
    return {"count": len(out), "predictions": out}
