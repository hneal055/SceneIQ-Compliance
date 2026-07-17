"""
tier_config.py - VPS-1: tier-aware production baselines.

The 8-page/day standard is an indie-feature norm. Vertical micro-serials
(1-3 day shoots, dialogue-heavy, 15-25 pages/day) score falsely critical
against it. This module gives every engine one place to ask: what is
normal for THIS production?
"""

_TIER_STANDARDS = {
    # pages_per_day: the standard against which overload/OT is measured
    # contingency_norm_pct: what "thin contingency" means for the tier
    "vertical": {"pages_per_day": 20.0, "contingency_norm_pct": 7.5,
                 "label": "Vertical / micro-serial"},
    "micro":    {"pages_per_day": 8.0,  "contingency_norm_pct": 10.0,
                 "label": "Micro-budget feature"},
    "low":      {"pages_per_day": 8.0,  "contingency_norm_pct": 10.0,
                 "label": "Low-budget indie"},
    "mid":      {"pages_per_day": 8.0,  "contingency_norm_pct": 10.0,
                 "label": "Mid-budget indie"},
    "premium":  {"pages_per_day": 8.0,  "contingency_norm_pct": 10.0,
                 "label": "Premium"},
}
_DEFAULT = _TIER_STANDARDS["low"]


def tier_standards(production) -> dict:
    """Return the standards dict for a production's tier (safe default)."""
    tier = (getattr(production, "productionTier", None) or "").strip().lower()
    return _TIER_STANDARDS.get(tier, _DEFAULT)


def pages_standard(production) -> float:
    return tier_standards(production)["pages_per_day"]
