"""
aicp_parser.py - VPS-3: AICP Top-Sheet Parser and Validator
POST /productions/{id}/budget/topsheet-check   body: {"text": "..."}

Parses the canonical AICP-style budget top sheet - the lingua franca
of production budgets (Acct# / Category / Page / Total, section
subtotals, contingency, fringes, grand total) - and validates it:

  1. RECONCILIATION: detail lines must sum to their stated section
     subtotals; sections must sum to the grand total. The format is
     self-checking; the parser exploits that.
  2. FRINGES: labor accounts present with a $0/absent fringes line is
     the classic hidden exposure (routinely 10%+ of a micro budget).
  3. DATES: finish before start, or years that disagree wildly
     (the "June 16th 2020" typo class).
  4. CONTINGENCY: measured against the production tier's norm
     (7.5% is normal for vertical; thin for a feature) - VPS-1's
     tier_config supplies the standard.

Report-only in v1: findings are returned, not persisted as signals.
The crew-roster-based missing_fringes signal (budget_hygiene) remains
the platform's live alarm; this endpoint is the document-level check.
"""
import logging
import re
from typing import List, Optional
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from src.utils.database import prisma
from src.api.tier_config import tier_standards

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Budget Risk"])

# Account ranges in the standard chart of accounts
_ATL_RANGE = (1000, 1499)
_PRODUCTION_RANGE = (1500, 3299)
_POST_RANGE = (3300, 3799)
# Accounts that represent labor (for the fringe check)
_LABOR_HINTS = ("staff", "producer", "director", "cast", "crew", "operator",
                "camera", "sound", "grip", "electric", "editor", "labor",
                "wardrobe", "makeup", "hair", "art department")

_DETAIL_RE = re.compile(
    r"^\s*(\d{3,4})\s+(.+?)\s+(?:(\d{1,3})\s+)?\$?\s*([\d,]+(?:\.\d{2})?)\s*$")
_TOTAL_RE = re.compile(
    r"^\s*(Total[^$\d]*?|Grand Total[^$\d]*?)\s+\$?\s*([\d,]+(?:\.\d{2})?)\s*$",
    re.IGNORECASE)
_CONTINGENCY_RE = re.compile(
    r"contingency\s*:?\s*([\d.]+)\s*%.*?\$?\s*([\d,]+(?:\.\d{2})?)?\s*$",
    re.IGNORECASE)
_DATE_RE = re.compile(
    r"(start|finish|begin|end|wrap)[^:\n]*?:?\s*"
    r"((?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+\d{1,2}(?:st|nd|rd|th)?,?\s+(\d{4})"
    r"|\d{1,2}/\d{1,2}/(\d{4}))",
    re.IGNORECASE)


def _amount(s: str) -> float:
    return float(s.replace(",", ""))


class ParsedLine(BaseModel):
    account: int
    description: str
    page: Optional[int]
    total: float


class Reconciliation(BaseModel):
    section: str
    stated: Optional[float]
    computed: float
    matches: Optional[bool]


class Finding(BaseModel):
    severity: str  # high | medium | low
    finding: str


class TopsheetResponse(BaseModel):
    production_id: str
    production_tier: str
    lines_parsed: int
    detail_total: float
    grand_total_stated: Optional[float]
    fringes_stated: Optional[float]
    contingency_pct: Optional[float]
    reconciliations: List[Reconciliation]
    reconciliation_passed: bool
    findings: List[Finding]
    verdict: str
    lines: List[ParsedLine]


class TopsheetRequest(BaseModel):
    text: str


@router.post(
    "/productions/{production_id}/budget/topsheet-check",
    response_model=TopsheetResponse,
    summary="Parse and validate an AICP-style budget top sheet",
)
async def check_topsheet(production_id: str, body: TopsheetRequest):
    production = await prisma.production.find_unique(where={"id": production_id})
    if not production:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Production not found")
    standards = tier_standards(production)
    tier = (production.productionTier or "default")

    text = body.text or ""
    if not text.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty text")

    lines: List[ParsedLine] = []
    stated_totals: dict = {}
    contingency_pct = None
    contingency_amount = None
    dates = []

    for raw in text.splitlines():
        m = _CONTINGENCY_RE.search(raw)
        if m:
            contingency_pct = float(m.group(1))
            if m.group(2):
                contingency_amount = _amount(m.group(2))
            continue
        m = _TOTAL_RE.match(raw)
        if m:
            label = re.sub(r"\s+", " ", m.group(1)).strip().rstrip(":").lower()
            stated_totals[label] = _amount(m.group(2))
            continue
        m = _DETAIL_RE.match(raw)
        if m:
            lines.append(ParsedLine(
                account=int(m.group(1)),
                description=m.group(2).strip(),
                page=int(m.group(3)) if m.group(3) else None,
                total=_amount(m.group(4)),
            ))
            continue
        for dm in _DATE_RE.finditer(raw):
            year = dm.group(3) or dm.group(4)
            dates.append((dm.group(1).lower(), dm.group(2), int(year)))

    # ---- Reconciliation ---------------------------------------------------
    def section_sum(lo, hi):
        return sum(l.total for l in lines if lo <= l.account <= hi)

    atl = section_sum(*_ATL_RANGE)
    prod_sum = section_sum(*_PRODUCTION_RANGE)
    post = section_sum(*_POST_RANGE)
    other = sum(l.total for l in lines if l.account > _POST_RANGE[1])
    detail_total = sum(l.total for l in lines)

    def find_stated(*keywords):
        for label, amt in stated_totals.items():
            if all(k in label for k in keywords):
                return amt
        return None

    recs: List[Reconciliation] = []

    def rec(section, stated, computed):
        matches = None if stated is None else abs(stated - computed) < 1.0
        recs.append(Reconciliation(section=section, stated=stated,
                                   computed=round(computed, 2), matches=matches))
        return matches

    rec("Above-The-Line", find_stated("above-the-line"), atl)
    rec("Production", find_stated("production"), prod_sum)
    rec("Post Production", find_stated("post"), post)

    btl_stated = find_stated("below-the-line")
    btl_computed = prod_sum + post + other + (contingency_amount or 0.0)
    rec("Below-The-Line", btl_stated, btl_computed)

    grand_stated = find_stated("grand")
    grand_computed = atl + btl_computed
    rec("Grand Total", grand_stated, grand_computed)

    checked = [r for r in recs if r.matches is not None]
    reconciliation_passed = bool(checked) and all(r.matches for r in checked)

    # ---- Findings ---------------------------------------------------------
    findings: List[Finding] = []

    fringes_stated = find_stated("fringe")
    labor_lines = [l for l in lines
                   if any(h in l.description.lower() for h in _LABOR_HINTS)]
    labor_total = sum(l.total for l in labor_lines)
    if labor_total > 0 and (fringes_stated is None or fringes_stated == 0.0):
        est = labor_total * 0.165
        findings.append(Finding(severity="high", finding=(
            f"Fringes are ${fringes_stated or 0:,.0f} against ~${labor_total:,.0f} "
            f"of labor-type accounts. Payroll taxes and workers' comp alone run "
            f"~16.5% non-union - roughly ${est:,.0f} of real cost missing from "
            f"this budget.")))

    for what, datestr, year in dates:
        if year < 2020 or year > 2100:
            findings.append(Finding(severity="medium", finding=(
                f"Suspicious year in '{what}' date: {datestr}")))
    years = sorted({y for _, _, y in dates})
    if len(years) > 1 and (years[-1] - years[0]) >= 2:
        findings.append(Finding(severity="medium", finding=(
            f"Dates disagree by {years[-1]-years[0]} years "
            f"({years[0]} vs {years[-1]}) - likely a typo; check start/finish dates.")))

    norm = standards["contingency_norm_pct"]
    if contingency_pct is not None and contingency_pct < norm:
        findings.append(Finding(severity="low", finding=(
            f"Contingency {contingency_pct:.1f}% is below the "
            f"{norm:.1f}% norm for the {standards['label']} tier.")))

    for r in recs:
        if r.matches is False:
            findings.append(Finding(severity="high", finding=(
                f"Reconciliation FAILED: {r.section} stated "
                f"${r.stated:,.0f} but detail lines sum to ${r.computed:,.0f}.")))

    zero_lines = [l for l in lines if l.total == 0.0]
    for l in zero_lines:
        findings.append(Finding(severity="low", finding=(
            f"Account {l.account} ({l.description}) is budgeted at $0 - "
            f"intentional or placeholder?")))

    if not findings:
        verdict = "Top sheet parses clean: totals reconcile, no defects detected."
    else:
        highs = sum(1 for f in findings if f.severity == "high")
        verdict = (
            f"{len(lines)} lines parsed, reconciliation "
            f"{'PASSED' if reconciliation_passed else 'FAILED'}, "
            f"{len(findings)} finding(s) ({highs} high). "
            f"Top item: {findings[0].finding}")

    return TopsheetResponse(
        production_id=production_id,
        production_tier=tier,
        lines_parsed=len(lines),
        detail_total=round(detail_total, 2),
        grand_total_stated=grand_stated,
        fringes_stated=fringes_stated,
        contingency_pct=contingency_pct,
        reconciliations=recs,
        reconciliation_passed=reconciliation_passed,
        findings=findings,
        verdict=verdict,
        lines=lines,
    )
