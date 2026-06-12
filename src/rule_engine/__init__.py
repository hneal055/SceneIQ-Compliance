"""
Rule Engine package (canonical exports)

Keep this file in sync with registry.py / engine.py public APIs.
"""

from .engine import evaluate, evaluate_rule, EvalResult
from .registry import (
    get_rules_dir,
    ensure_rules_dir,
    normalize_code,
    rule_filename,
    find_rule_path,
    get_rule_path,
    list_rule_codes,
)

__all__ = [
    "evaluate",
    "evaluate_rule",
    "EvalResult",
    "get_rules_dir",
    "ensure_rules_dir",
    "normalize_code",
    "rule_filename",
    "find_rule_path",
    "get_rule_path",
    "list_rule_codes",
]


