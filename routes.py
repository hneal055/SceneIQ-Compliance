"""
Main API router - aggregates all route modules
"""
from fastapi import APIRouter, Depends

from src.api.auth import router as auth_router
from src.api.jurisdictions import router as jurisdictions_router
from src.api.incentive_rules import router as incentive_rules_router
from src.api.productions import router as productions_router
from src.api.calculator import router as calculator_router
from src.api.reports import router as reports_router
from src.api.excel import router as excel_router
from src.api.rule_engine import router as rule_engine_router
from src.api.monitoring import router as monitoring_router
from src.api.georgia import router as georgia_router
from src.api.largo import router as largo_router
from src.api.advisor import router as advisor_router
from src.api.compliance import router as compliance_router
from src.api.notifications import router as notifications_router
from src.api.admin import router as admin_router
from src.api.production_expenses import router as production_expenses_router
from src.api.pending_rules import router as pending_rules_router
from src.api.local_rules import router as local_rules_router
from src.api.stacking_engine import router as stacking_engine_router
from src.api.maximizer import router as maximizer_router
from src.api.requirements import router as requirements_router
from src.api.scenarios import router as scenarios_router
from src.api.schedule_parser import router as schedule_parser_router
from src.api.production_schedule import router as production_schedule_router
from src.api.conflicts import router as conflicts_router
from src.api.pipeline import router as pipeline_router
from src.api.signals import router as signals_router
from src.utils.auth_utils import get_current_user

API_PREFIX = "/api/0.1.0"

router = APIRouter()

_auth_dep = [Depends(get_current_user)]

# Public — no auth required
router.include_router(auth_router)

# Protected — JWT required
router.include_router(jurisdictions_router, dependencies=_auth_dep)
router.include_router(incentive_rules_router, dependencies=_auth_dep)
router.include_router(productions_router, dependencies=_auth_dep)
router.include_router(calculator_router, dependencies=_auth_dep)
router.include_router(reports_router, dependencies=_auth_dep)
router.include_router(excel_router, dependencies=_auth_dep)
router.include_router(rule_engine_router, dependencies=_auth_dep)
router.include_router(monitoring_router, dependencies=_auth_dep)
router.include_router(advisor_router, dependencies=_auth_dep)
router.include_router(compliance_router, dependencies=_auth_dep)
router.include_router(notifications_router, dependencies=_auth_dep)
router.include_router(admin_router, dependencies=_auth_dep)
router.include_router(production_expenses_router, dependencies=_auth_dep)
router.include_router(georgia_router, dependencies=_auth_dep)
router.include_router(pending_rules_router, dependencies=_auth_dep)
router.include_router(local_rules_router, dependencies=_auth_dep)
router.include_router(stacking_engine_router, dependencies=_auth_dep)
router.include_router(maximizer_router, dependencies=_auth_dep)
router.include_router(requirements_router, dependencies=_auth_dep)
router.include_router(scenarios_router, dependencies=_auth_dep)
router.include_router(schedule_parser_router, dependencies=_auth_dep)
router.include_router(production_schedule_router, dependencies=_auth_dep)
router.include_router(conflicts_router, dependencies=_auth_dep)
router.include_router(pipeline_router, dependencies=_auth_dep)
router.include_router(signals_router, dependencies=_auth_dep)


@router.get("/", tags=["Meta"])
async def api_root():
    """API root endpoint (under /api/0.1.0/)"""
    return {
        "message": "Tax Incentive Compliance Platform API",
        "version": "1.0.0",
        "endpoints": {
            "jurisdictions": f"{API_PREFIX}/jurisdictions/",
            "incentive_rules": f"{API_PREFIX}/incentive-rules/",
            "productions": f"{API_PREFIX}/productions/",
            "calculator_simple": f"{API_PREFIX}/calculate/simple",
            "calculator_compare": f"{API_PREFIX}/calculate/compare",
            "reports": f"{API_PREFIX}/reports",
            "excel": f"{API_PREFIX}/excel",
            "health": "/health",
        },
    }
