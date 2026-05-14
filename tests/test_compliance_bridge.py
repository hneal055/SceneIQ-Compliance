# =============================================================================
# tests/test_compliance_bridge.py
# Phase 9 verification — exercises the ComplianceBridge at
# src/services/production_schedule/bridge/compliance_bridge.py.
#
# Shared fixture mirrors the user's spec:
#   - Georgia       — 3 shoot days, verified
#   - New York      — 2 shoot days, verified (MMB says 5 days → variance 3)
#   - California    — 1 shoot day, UNVERIFIED (excluded by push function)
# =============================================================================

from datetime import datetime, timezone

import pytest

from src.services.production_schedule.bridge.compliance_bridge import (
    get_compliance_data_summary,
    push_shoot_days_to_calculator,
    reconcile_with_mmb,
)
from src.services.production_schedule.models.jurisdiction_shoot_days import (
    JurisdictionShootDays,
)


VERIFIED_AT = datetime(2026, 5, 14, 12, 0, tzinfo=timezone.utc)


@pytest.fixture
def records():
    return [
        JurisdictionShootDays(
            production_id="prod-test",
            jurisdiction_id="Georgia",
            shoot_days=3,
            verified_at=VERIFIED_AT,
        ),
        JurisdictionShootDays(
            production_id="prod-test",
            jurisdiction_id="New York",
            shoot_days=2,
            verified_at=VERIFIED_AT,
        ),
        JurisdictionShootDays(
            production_id="prod-test",
            jurisdiction_id="California",
            shoot_days=1,
            verified_at=None,  # unverified — push function must skip
        ),
    ]


@pytest.fixture
def mmb_data():
    return {
        "Georgia":  {"spend_days": 3, "qualified_spend": 850_000.0},
        "New York": {"spend_days": 5, "qualified_spend": 1_200_000.0},
    }


@pytest.fixture
def credit_estimates():
    return {"Georgia": 255_000.0, "New York": 240_000.0}


def test_push_shoot_days_excludes_unverified(records):
    payload = push_shoot_days_to_calculator("prod-test", records)
    assert set(payload.keys()) == {"Georgia", "New York"}
    assert "California" not in payload

    assert payload["Georgia"] == {"shoot_days": 3, "verified_at": VERIFIED_AT}
    assert payload["New York"] == {"shoot_days": 2, "verified_at": VERIFIED_AT}


def test_reconcile_match_true_when_counts_agree(records, mmb_data):
    rows = reconcile_with_mmb("prod-test", records, mmb_data)
    georgia = next(r for r in rows if r["jurisdiction"] == "Georgia")
    assert georgia["shoot_days_from_stripboard"] == 3
    assert georgia["spend_days_from_mmb"] == 3
    assert georgia["match"] is True
    assert georgia["variance"] == 0


def test_reconcile_match_false_when_counts_differ(records, mmb_data):
    rows = reconcile_with_mmb("prod-test", records, mmb_data)
    new_york = next(r for r in rows if r["jurisdiction"] == "New York")
    assert new_york["shoot_days_from_stripboard"] == 2
    assert new_york["spend_days_from_mmb"] == 5
    assert new_york["match"] is False
    assert new_york["variance"] == 3


def test_reconcile_variance_calculation_both_directions():
    """abs() should handle stripboard > MMB and stripboard < MMB
    symmetrically."""
    records = [
        JurisdictionShootDays(
            production_id="prod-test",
            jurisdiction_id="A",
            shoot_days=7,           # stripboard higher than MMB
            verified_at=VERIFIED_AT,
        ),
        JurisdictionShootDays(
            production_id="prod-test",
            jurisdiction_id="B",
            shoot_days=2,           # stripboard lower than MMB
            verified_at=VERIFIED_AT,
        ),
    ]
    mmb = {"A": {"spend_days": 4}, "B": {"spend_days": 6}}

    rows = reconcile_with_mmb("prod-test", records, mmb)
    a = next(r for r in rows if r["jurisdiction"] == "A")
    b = next(r for r in rows if r["jurisdiction"] == "B")

    assert a["variance"] == 3   # |7 - 4|
    assert b["variance"] == 4   # |2 - 6|
    assert a["match"] is False
    assert b["match"] is False


def test_get_compliance_data_summary_merges_sources(records, mmb_data, credit_estimates):
    summary = get_compliance_data_summary(
        "prod-test", records, mmb_data, credit_estimates
    )

    # One entry per record.
    assert set(summary.keys()) == {"Georgia", "New York", "California"}

    georgia = summary["Georgia"]
    assert georgia == {
        "shoot_days":       3,
        "verified_at":      VERIFIED_AT,
        "qualified_spend":  850_000.0,
        "estimated_credit": 255_000.0,
    }

    new_york = summary["New York"]
    assert new_york["shoot_days"] == 2
    assert new_york["qualified_spend"] == 1_200_000.0
    assert new_york["estimated_credit"] == 240_000.0

    # California: no MMB data, no estimate, unverified.
    california = summary["California"]
    assert california == {
        "shoot_days":       1,
        "verified_at":      None,
        "qualified_spend":  None,
        "estimated_credit": None,
    }


def test_missing_mmb_and_credit_render_as_none(records):
    """The user's contract: missing downstream data renders as None,
    never raises."""
    summary = get_compliance_data_summary(
        "prod-test",
        records,
        mmb_data=None,
        credit_estimates=None,
    )

    assert set(summary.keys()) == {"Georgia", "New York", "California"}
    for jid in summary:
        assert summary[jid]["qualified_spend"] is None
        assert summary[jid]["estimated_credit"] is None
        # shoot_days and verified_at still come from the records
        assert "shoot_days" in summary[jid]
        assert "verified_at" in summary[jid]
