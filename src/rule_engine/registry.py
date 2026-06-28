"""
Rule registry (canonical)

Source of truth:
  - Rules directory defaults to: <repo_root>/rules
  - Rule filename convention: <CODE>.json (uppercase)

Behavior:
  - get_rule_path(code) raises FileNotFoundError if not found
  - find_rule_path(code) returns Optional[Path]
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional, Set

# src/rule_engine/registry.py -> parents[2] is repo root (repo/src/rule_engine/registry.py)
REPO_ROOT = Path(__file__).resolve().parents[2]

# Optional override (but the canonical default is repo_root/rules)
_RULES_DIR_ENV = "TAX_RULES_DIR"


def get_rules_dir() -> Path:
    """
    Returns the rules directory.

    Canonical default: <repo_root>/rules
    Override: TAX_RULES_DIR (absolute or relative to repo root)
    """
    override = (os.getenv(_RULES_DIR_ENV) or "").strip()
    if override:
        p = Path(override)
        return p if p.is_absolute() else (REPO_ROOT / p).resolve()
    return (REPO_ROOT / "rules").resolve()


def normalize_code(code: str) -> str:
    return (code or "").strip().upper()


def rule_filename(code: str) -> str:
    return f"{normalize_code(code)}.json"


def find_rule_path(code: str) -> Optional[Path]:
    """
    Returns the rule file path if it exists, else None.
    """
    rules_dir = get_rules_dir()
    c = normalize_code(code)
    if not c:
        return None

    candidate = rules_dir / rule_filename(c)
    return candidate if candidate.is_file() else None


def get_rule_path(code: str) -> Path:
    """
    Returns the rule file path or raises FileNotFoundError.
    """
    p = find_rule_path(code)
    if not p:
        rules_dir = get_rules_dir()
        c = normalize_code(code) or "<empty>"
        raise FileNotFoundError(f"Rule file not found for jurisdiction '{c}' in {rules_dir}")
    return p


def list_rule_codes() -> Set[str]:
    """
    Lists available jurisdiction codes from the rules directory.
    """
    rules_dir = get_rules_dir()
    if not rules_dir.exists():
        return set()

    codes: Set[str] = set()
    for f in rules_dir.glob("*.json"):
        if f.is_file():
            codes.add(f.stem.upper())
    return codes


def ensure_rules_dir() -> Path:
    """
    Creates the canonical rules directory if missing.
    """
    rules_dir = get_rules_dir()
    rules_dir.mkdir(parents=True, exist_ok=True)
    return rules_dir



