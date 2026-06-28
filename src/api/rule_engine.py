"""
Rule Engine API

Contract stability:
- Always return (default): jurisdiction_code, total_eligible_spend, total_incentive_amount, breakdown[]
- Tight payload by default (no trace/meta unless debug=true)
- Error mapping:
    * Unknown jurisdiction/rule file -> 404
    * Bad request payload -> 422 (FastAPI)
    * Engine runtime error -> 500 (safe message)
- Optional debug: ?debug=true adds trace/meta/warnings
"""
from __future__ import annotations

import logging
from fastapi import APIRouter, HTTPException, Query
from pydantic import ValidationError

from src.rule_engine.engine import evaluate
from src.rule_engine.models import EvaluateRequest, EvaluateResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/rule-engine", tags=["rule-engine"])


def _tight_contract(res: EvaluateResponse) -> dict:
    """
    Default response contract: tight + stable.
    """
    return {
        "jurisdiction_code": res.jurisdiction_code,
        "total_eligible_spend": res.total_eligible_spend,
        "total_incentive_amount": res.total_incentive_amount,
        "breakdown": res.breakdown,
    }


@router.post("/evaluate")
async def evaluate_rule_engine(
    req: EvaluateRequest,
    debug: bool = Query(False, description="Include debug trace/meta in response"),
):
    try:
        res = evaluate(req)

        if not debug:
            return _tight_contract(res)

        # Debug=true -> return full model (includes warnings/meta/trace if present)
        return res.model_dump()

    except FileNotFoundError as e:
        # Unknown jurisdiction/rule file -> 404
        raise HTTPException(status_code=404, detail=str(e)) from e

    except ValueError as e:
        # Engine-level "bad request" style errors (if any)
        raise HTTPException(status_code=400, detail=str(e)) from e

    except ValidationError as e:
        # If engine returned something that can't validate to EvaluateResponse
        logger.exception("Rule engine response validation error")
        raise HTTPException(status_code=500, detail="Rule engine response schema invalid") from e

    except Exception as e:
        logger.exception("Unhandled rule engine error")
        raise HTTPException(status_code=500, detail="Internal Server Error") from e




