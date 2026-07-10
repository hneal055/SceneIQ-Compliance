"""


async def _trigger_budget_analysis(production_id: str) -> None:
    try:
        from src.api.budget_risk import analyze_budget
        await analyze_budget(production_id)
    except Exception:
        logger.exception('budget drift auto-analysis failed for %s', production_id)
"""


"""
Production-scoped expense endpoints — nested under /productions/{id}/expenses.
Matches the URL pattern expected by the frontend API client.
"""
import logging
import os
from typing import Optional
from datetime import date, timedelta

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
import httpx

from src.utils.database import prisma

from src.api.atl_btl import router as atl_btl_router
from src.api.budget_risk import router as budget_risk_router
router = APIRouter(tags=["Expenses"])

# ---------------------------------------------------------------------------
# Budget allocation templates  (pct of total budget per line item)
# qualifying = eligible for film tax credit in most jurisdictions
# ---------------------------------------------------------------------------

_TEMPLATES: dict[str, list[dict]] = {
    "feature_film": [
        # Above-the-Line — typically NOT qualifying
        {"cat": "labor",          "desc": "Director",                       "pct": 0.08,  "q": False, "vendor": ""},
        {"cat": "labor",          "desc": "Executive Producer",             "pct": 0.04,  "q": False, "vendor": ""},
        {"cat": "labor",          "desc": "Lead Actor — Principal",         "pct": 0.08,  "q": False, "vendor": "Talent Agency Inc."},
        {"cat": "labor",          "desc": "Supporting Cast",                "pct": 0.05,  "q": False, "vendor": ""},
        {"cat": "labor",          "desc": "Screenplay / Story Rights",      "pct": 0.03,  "q": False, "vendor": ""},
        # Below-the-Line Labor — qualifying
        {"cat": "labor",          "desc": "Director of Photography",        "pct": 0.05,  "q": True,  "vendor": ""},
        {"cat": "labor",          "desc": "Production Manager",             "pct": 0.025, "q": True,  "vendor": ""},
        {"cat": "labor",          "desc": "1st Assistant Director",         "pct": 0.02,  "q": True,  "vendor": ""},
        {"cat": "labor",          "desc": "Gaffer / Lighting Crew",         "pct": 0.025, "q": True,  "vendor": ""},
        {"cat": "labor",          "desc": "Sound Mixer",                    "pct": 0.02,  "q": True,  "vendor": ""},
        {"cat": "labor",          "desc": "Production Designer",            "pct": 0.025, "q": True,  "vendor": ""},
        {"cat": "labor",          "desc": "Camera Crew",                    "pct": 0.02,  "q": True,  "vendor": ""},
        # Equipment — qualifying
        {"cat": "equipment",      "desc": "Camera Package Rental",         "pct": 0.05,  "q": True,  "vendor": "Panavision"},
        {"cat": "equipment",      "desc": "Lighting & Grip Package",        "pct": 0.04,  "q": True,  "vendor": ""},
        {"cat": "equipment",      "desc": "Sound Package",                  "pct": 0.02,  "q": True,  "vendor": ""},
        # Locations — qualifying
        {"cat": "locations",      "desc": "Location Fees",                  "pct": 0.04,  "q": True,  "vendor": ""},
        {"cat": "locations",      "desc": "Studio / Stage Rental",          "pct": 0.03,  "q": True,  "vendor": ""},
        {"cat": "locations",      "desc": "Location Permits",               "pct": 0.01,  "q": True,  "vendor": "Film Office"},
        # Travel & Living — qualifying
        {"cat": "travel",         "desc": "Air Travel — Cast & Crew",       "pct": 0.015, "q": True,  "vendor": ""},
        {"cat": "travel",         "desc": "Hotels — Production",            "pct": 0.015, "q": True,  "vendor": ""},
        {"cat": "travel",         "desc": "Ground Transportation",          "pct": 0.01,  "q": True,  "vendor": ""},
        # Catering — qualifying
        {"cat": "catering",       "desc": "Craft Services (daily)",         "pct": 0.01,  "q": True,  "vendor": ""},
        {"cat": "catering",       "desc": "Catering — Meals on Set",        "pct": 0.01,  "q": True,  "vendor": ""},
        # Post Production — qualifying
        {"cat": "post_production","desc": "Picture Editor",                 "pct": 0.04,  "q": True,  "vendor": ""},
        {"cat": "post_production","desc": "Color Grading",                  "pct": 0.015, "q": True,  "vendor": ""},
        {"cat": "post_production","desc": "Sound Edit & Mix",               "pct": 0.015, "q": True,  "vendor": ""},
        {"cat": "post_production","desc": "Visual Effects",                 "pct": 0.02,  "q": True,  "vendor": ""},
        {"cat": "post_production","desc": "Music Licensing & Score",        "pct": 0.01,  "q": True,  "vendor": ""},
        # Insurance / Legal — NOT qualifying
        {"cat": "insurance",      "desc": "Production Insurance",           "pct": 0.025, "q": False, "vendor": ""},
        {"cat": "legal",          "desc": "Legal & E&O Insurance",          "pct": 0.01,  "q": False, "vendor": ""},
        {"cat": "other",          "desc": "Contingency Reserve",            "pct": 0.02,  "q": False, "vendor": ""},
    ],
    "documentary": [
        {"cat": "labor",          "desc": "Director / Producer",            "pct": 0.10,  "q": False, "vendor": ""},
        {"cat": "labor",          "desc": "Lead Researcher",                "pct": 0.05,  "q": False, "vendor": ""},
        {"cat": "labor",          "desc": "Archive Licensing",              "pct": 0.04,  "q": False, "vendor": "Archive Inc."},
        {"cat": "labor",          "desc": "Director of Photography",        "pct": 0.07,  "q": True,  "vendor": ""},
        {"cat": "labor",          "desc": "Production Manager",             "pct": 0.04,  "q": True,  "vendor": ""},
        {"cat": "labor",          "desc": "Sound Recordist",                "pct": 0.03,  "q": True,  "vendor": ""},
        {"cat": "equipment",      "desc": "Camera Package",                 "pct": 0.07,  "q": True,  "vendor": ""},
        {"cat": "equipment",      "desc": "Lighting Package",               "pct": 0.04,  "q": True,  "vendor": ""},
        {"cat": "equipment",      "desc": "Sound Package",                  "pct": 0.02,  "q": True,  "vendor": ""},
        {"cat": "locations",      "desc": "Location Fees",                  "pct": 0.05,  "q": True,  "vendor": ""},
        {"cat": "locations",      "desc": "Location Permits",               "pct": 0.01,  "q": True,  "vendor": "Film Office"},
        {"cat": "travel",         "desc": "Air Travel — Crew",              "pct": 0.04,  "q": True,  "vendor": ""},
        {"cat": "travel",         "desc": "Hotels & Per Diem",              "pct": 0.04,  "q": True,  "vendor": ""},
        {"cat": "catering",       "desc": "Craft Services",                 "pct": 0.015, "q": True,  "vendor": ""},
        {"cat": "post_production","desc": "Picture Editor",                 "pct": 0.09,  "q": True,  "vendor": ""},
        {"cat": "post_production","desc": "Color Grading",                  "pct": 0.03,  "q": True,  "vendor": ""},
        {"cat": "post_production","desc": "Sound Edit & Mix",               "pct": 0.03,  "q": True,  "vendor": ""},
        {"cat": "post_production","desc": "Music Score",                    "pct": 0.02,  "q": True,  "vendor": ""},
        {"cat": "insurance",      "desc": "Production Insurance",           "pct": 0.03,  "q": False, "vendor": ""},
        {"cat": "legal",          "desc": "Legal",                          "pct": 0.015, "q": False, "vendor": ""},
        {"cat": "other",          "desc": "Contingency Reserve",            "pct": 0.025, "q": False, "vendor": ""},
    ],
    "tv_series": [
        # Above-the-Line — NOT qualifying
        {"cat": "labor",          "desc": "Showrunner / EP",                "pct": 0.10,  "q": False, "vendor": ""},
        {"cat": "labor",          "desc": "Writers' Room (4 writers)",      "pct": 0.06,  "q": False, "vendor": ""},
        {"cat": "labor",          "desc": "Director(s)",                    "pct": 0.05,  "q": False, "vendor": ""},
        {"cat": "labor",          "desc": "Series Lead Cast",               "pct": 0.09,  "q": False, "vendor": "Talent Agency"},
        {"cat": "labor",          "desc": "Supporting Cast",                "pct": 0.05,  "q": False, "vendor": ""},
        # BTL — qualifying
        {"cat": "labor",          "desc": "Director of Photography",        "pct": 0.04,  "q": True,  "vendor": ""},
        {"cat": "labor",          "desc": "Production Manager",             "pct": 0.025, "q": True,  "vendor": ""},
        {"cat": "labor",          "desc": "Line Producer",                  "pct": 0.02,  "q": True,  "vendor": ""},
        {"cat": "labor",          "desc": "Crew — Camera, Sound, Grip",     "pct": 0.04,  "q": True,  "vendor": ""},
        {"cat": "labor",          "desc": "Production Designer",            "pct": 0.02,  "q": True,  "vendor": ""},
        {"cat": "equipment",      "desc": "Camera Package",                 "pct": 0.05,  "q": True,  "vendor": ""},
        {"cat": "equipment",      "desc": "Lighting Package",               "pct": 0.045, "q": True,  "vendor": ""},
        {"cat": "locations",      "desc": "Studio / Stage Rental",          "pct": 0.045, "q": True,  "vendor": ""},
        {"cat": "locations",      "desc": "Street Permits & Location Fees", "pct": 0.025, "q": True,  "vendor": "Film Office"},
        {"cat": "travel",         "desc": "Air Travel",                     "pct": 0.015, "q": True,  "vendor": ""},
        {"cat": "travel",         "desc": "Hotels — Key Talent",            "pct": 0.015, "q": True,  "vendor": ""},
        {"cat": "catering",       "desc": "Craft Services (per episode)",   "pct": 0.01,  "q": True,  "vendor": ""},
        {"cat": "catering",       "desc": "Catering — Meals on Set",        "pct": 0.01,  "q": True,  "vendor": ""},
        {"cat": "post_production","desc": "Picture Editor",                 "pct": 0.035, "q": True,  "vendor": ""},
        {"cat": "post_production","desc": "Color Grading (per episode)",    "pct": 0.02,  "q": True,  "vendor": ""},
        {"cat": "post_production","desc": "Sound Edit & Mix (per episode)", "pct": 0.02,  "q": True,  "vendor": ""},
        {"cat": "post_production","desc": "Visual Effects",                 "pct": 0.015, "q": True,  "vendor": ""},
        {"cat": "insurance",      "desc": "Production Insurance",           "pct": 0.025, "q": False, "vendor": ""},
        {"cat": "legal",          "desc": "Legal & Clearances",             "pct": 0.01,  "q": False, "vendor": ""},
        {"cat": "other",          "desc": "Contingency Reserve",            "pct": 0.02,  "q": False, "vendor": ""},
    ],
    "short_film": [
        {"cat": "labor",          "desc": "Director / Writer",              "pct": 0.12,  "q": False, "vendor": ""},
        {"cat": "labor",          "desc": "Cast",                           "pct": 0.06,  "q": False, "vendor": ""},
        {"cat": "labor",          "desc": "Director of Photography",        "pct": 0.08,  "q": True,  "vendor": ""},
        {"cat": "labor",          "desc": "Crew",                           "pct": 0.08,  "q": True,  "vendor": ""},
        {"cat": "equipment",      "desc": "Camera & Lighting Package",      "pct": 0.10,  "q": True,  "vendor": ""},
        {"cat": "locations",      "desc": "Location Fees & Permits",        "pct": 0.07,  "q": True,  "vendor": ""},
        {"cat": "catering",       "desc": "Craft Services & Meals",         "pct": 0.04,  "q": True,  "vendor": ""},
        {"cat": "post_production","desc": "Editor",                         "pct": 0.10,  "q": True,  "vendor": ""},
        {"cat": "post_production","desc": "Color & Sound",                  "pct": 0.06,  "q": True,  "vendor": ""},
        {"cat": "insurance",      "desc": "Production Insurance",           "pct": 0.04,  "q": False, "vendor": ""},
        {"cat": "other",          "desc": "Miscellaneous",                  "pct": 0.05,  "q": False, "vendor": ""},
    ],
    "commercial": [
        {"cat": "labor",          "desc": "Director",                       "pct": 0.10,  "q": False, "vendor": ""},
        {"cat": "labor",          "desc": "Agency / Creative Fees",         "pct": 0.08,  "q": False, "vendor": ""},
        {"cat": "labor",          "desc": "Talent (on-screen)",             "pct": 0.07,  "q": False, "vendor": ""},
        {"cat": "labor",          "desc": "Director of Photography",        "pct": 0.06,  "q": True,  "vendor": ""},
        {"cat": "labor",          "desc": "Crew",                           "pct": 0.06,  "q": True,  "vendor": ""},
        {"cat": "equipment",      "desc": "Camera Package",                 "pct": 0.08,  "q": True,  "vendor": ""},
        {"cat": "equipment",      "desc": "Lighting & Grip",                "pct": 0.06,  "q": True,  "vendor": ""},
        {"cat": "locations",      "desc": "Studio Rental",                  "pct": 0.07,  "q": True,  "vendor": ""},
        {"cat": "locations",      "desc": "Location Permits",               "pct": 0.02,  "q": True,  "vendor": ""},
        {"cat": "travel",         "desc": "Travel & Per Diem",              "pct": 0.03,  "q": True,  "vendor": ""},
        {"cat": "catering",       "desc": "Craft Services & Meals",         "pct": 0.02,  "q": True,  "vendor": ""},
        {"cat": "post_production","desc": "Edit & Post",                    "pct": 0.12,  "q": True,  "vendor": ""},
        {"cat": "insurance",      "desc": "Production Insurance",           "pct": 0.03,  "q": False, "vendor": ""},
        {"cat": "other",          "desc": "Contingency",                    "pct": 0.03,  "q": False, "vendor": ""},
    ],
}

# Fall back to feature_film template for unknown types
_TEMPLATES["feature"] = _TEMPLATES["feature_film"]
_TEMPLATES["film"] = _TEMPLATES["feature_film"]

EXPENSE_CATEGORIES = [
    "labor", "equipment", "locations", "post_production",
    "travel", "catering", "legal", "insurance", "visual_effects", "other",
]


# ── Pydantic models

class ExpenseCreate(BaseModel):
    category:      str
    description:   str
    amount:        float
    expenseDate:   str           # ISO date string YYYY-MM-DD
    isQualifying:  bool = True
    vendorName:    Optional[str] = None
    subcategory:   Optional[str] = None
    qualifyingNote: Optional[str] = None


class BudgetImportRequest(BaseModel):
    budget_analysis_id: str


# ── Budget Analysis import — category classification ──────────────────────
# Pattern derived from this app's own _TEMPLATES above: every category
# qualifies consistently across all production types except "labor", which
# splits Above-the-Line (non-qualifying) vs Below-the-Line (qualifying).

BUDGET_ANALYSIS_API_URL = os.environ.get('BUDGET_ANALYSIS_API_URL', '')
BUDGET_ANALYSIS_API_KEY = os.environ.get('BUDGET_ANALYSIS_API_KEY', '')

# Role / person-indicating words are checked FIRST, before any other category.
# A line item that names a role (e.g. "Camera Operator", "Grip Crew") is a
# person's wage, not gear — it must land on labor and be flagged for manual
# Above-the-Line / Below-the-Line review, never auto-marked as qualifying.
# ("crew" and "operator" in particular used to be swallowed by the equipment
# rule, silently qualifying a $18k crew salary — see _classify_line_item.)
_LABOR_KEYWORDS = [
    "labor", "staff", "salary", "wage", "director", "actor",
    "cast", "talent", "operator", "crew", "technician", "artist",
    "coordinator", "supervisor", "producer", "assistant", "manager",
]
_LABOR_NOTE = (
    "Imported as labor — requires manual Above-the-Line / Below-the-Line "
    "review before it can be marked qualifying."
)

# Non-labor category rules, checked only AFTER labor has been ruled out.
# NOTE: "crew" was removed from the equipment rule and moved into
# _LABOR_KEYWORDS above — it names people, not equipment.
_CATEGORY_RULES: list[tuple[list[str], str, bool, str]] = [
    (["camera", "gear", "rental", "equipment"], "equipment", True,
     "Auto-classified as equipment (always qualifying)."),
    (["location", "permit", "stage", "studio"], "locations", True,
     "Auto-classified as locations (always qualifying)."),
    (["travel", "flight", "hotel", "transport"], "travel", True,
     "Auto-classified as travel (always qualifying)."),
    (["catering", "craft service", "craft services", "food", "meal"], "catering", True,
     "Auto-classified as catering (always qualifying)."),
    (["vfx", "visual effects", "cgi"], "visual_effects", True,
     "Auto-classified as visual effects (always qualifying)."),
    (["edit", "color", "sound mix", "post"], "post_production", True,
     "Auto-classified as post-production (always qualifying)."),
    (["legal"], "legal", False,
     "Auto-classified as legal (never qualifying)."),
    (["insurance"], "insurance", False,
     "Auto-classified as insurance (never qualifying)."),
]


def _classify_line_item(category: str, department: str = "") -> tuple[str, bool, str]:
    """Map a Budget Analysis line item's freeform category/department text
    onto a Compliance expense category, a default isQualifying flag, and an
    explanatory note.

    Labor/role-indicating words are checked FIRST: a line item naming a person
    (e.g. "Camera Operator") is a wage, not equipment, so it must be imported
    as labor and flagged for manual ATL/BTL review rather than silently marked
    qualifying. Only if no labor signal is present do we fall through to the
    equipment/locations/travel/etc. rules. Falls back to 'other' /
    non-qualifying when nothing matches, so an unclassifiable item is flagged
    rather than guessed at."""
    haystack = f"{category} {department}".lower()
    if any(kw in haystack for kw in _LABOR_KEYWORDS):
        return "labor", False, _LABOR_NOTE
    for keywords, mapped_category, qualifying, note in _CATEGORY_RULES:
        if any(kw in haystack for kw in keywords):
            return mapped_category, qualifying, note
    return "other", False, f"Could not confidently classify '{category}' — imported as other, non-qualifying. Please review."


# ── Routes ──────────────────────────────────────────────────────────────────

@router.get("/productions/{production_id}/expenses",
            summary="List expenses for a production")
async def list_expenses(production_id: str):
    prod = await prisma.production.find_unique(where={"id": production_id})
    if not prod:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Production not found")

    expenses = await prisma.expense.find_many(
        where={"productionId": production_id},
        order={"expenseDate": "desc"},
    )
    total_amount      = sum(e.amount for e in expenses)
    qualifying_amount = sum(e.amount for e in expenses if e.isQualifying)
    return {
        "total":            len(expenses),
        "totalAmount":      total_amount,
        "qualifyingAmount": qualifying_amount,
        "nonQualifyingAmount": total_amount - qualifying_amount,
        "expenses":         expenses,
    }


@router.post("/productions/{production_id}/expenses",
             status_code=status.HTTP_201_CREATED,
             summary="Add an expense to a production")
async def create_expense(production_id: str, data: ExpenseCreate):
    prod = await prisma.production.find_unique(where={"id": production_id})
    if not prod:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Production not found")

    if data.amount <= 0:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Amount must be positive")

    try:
        expense_date = date.fromisoformat(data.expenseDate)
    except ValueError:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Invalid expenseDate — use YYYY-MM-DD")

    create_data: dict = {
        "productionId": production_id,
        "category":     data.category,
        "description":  data.description,
        "amount":       data.amount,
        "expenseDate":  expense_date.isoformat() + "T00:00:00Z",
        "isQualifying": data.isQualifying,
        "source":       "manual",
    }
    if data.vendorName:     create_data["vendorName"]    = data.vendorName
    if data.subcategory:    create_data["subcategory"]   = data.subcategory
    if data.qualifyingNote: create_data["qualifyingNote"] = data.qualifyingNote

    expense = await prisma.expense.create(data=create_data)
    logger.info(f"Expense created: {expense.id} for production {production_id}")
    await _trigger_budget_analysis(production_id)
    return expense


@router.delete("/productions/{production_id}/expenses/{expense_id}",
               status_code=status.HTTP_204_NO_CONTENT,
               summary="Delete an expense")
async def delete_expense(production_id: str, expense_id: str):
    expense = await prisma.expense.find_unique(where={"id": expense_id})
    if not expense or expense.productionId != production_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Expense not found")
    await prisma.expense.delete(where={"id": expense_id})
    return None


@router.post("/productions/{production_id}/expenses/generate",
             status_code=status.HTTP_201_CREATED,
             summary="Auto-generate budget line items for a production")
async def generate_expenses(production_id: str, replace: bool = False):
    """
    Auto-generate realistic expense line items from a budget allocation template
    matched to the production's type and total budget.

    - replace=false (default): only generates if no expenses exist yet
    - replace=true: deletes all existing expenses first, then regenerates
    """
    prod = await prisma.production.find_unique(where={"id": production_id})
    if not prod:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Production not found")

    if not prod.budgetTotal or prod.budgetTotal <= 0:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Production must have a positive budgetTotal to generate line items."
        )

    # Check existing expenses
    existing = await prisma.expense.find_many(where={"productionId": production_id})
    if existing and not replace:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Production already has {len(existing)} expense(s). "
            "Pass ?replace=true to delete them and regenerate."
        )

    if replace and existing:
        await prisma.expense.delete_many(where={"productionId": production_id})
        logger.info(f"Deleted {len(existing)} existing expenses for production {production_id}")

    # Pick template
    prod_type = (prod.productionType or "feature_film").lower().replace(" ", "_")
    template = _TEMPLATES.get(prod_type) or _TEMPLATES["feature_film"]

    # Determine base date — use production start date if set, else today
    if prod.startDate:
        try:
            base = date.fromisoformat(str(prod.startDate)[:10])
        except ValueError:
            base = date.today()
    else:
        base = date.today()

    # Spread dates: pre-prod 4 wks before, production 0–8 wks, post 8–14 wks after base
    category_offset: dict[str, int] = {
        "labor":          -14,   # pre-prod / ATL deals signed early
        "equipment":       0,
        "locations":       -7,
        "travel":          7,
        "catering":        14,
        "post_production": 56,
        "visual_effects":  70,
        "insurance":       -21,
        "legal":           -21,
        "other":           0,
    }

    created = []
    for item in template:
        amount = round(prod.budgetTotal * item["pct"], 2)
        if amount <= 0:
            continue

        offset_days = category_offset.get(item["cat"], 0)
        expense_date = base + timedelta(days=offset_days)
        # Clamp to today max (don't create future-dated expenses)
        if expense_date > date.today():
            expense_date = date.today()

        create_data: dict = {
            "productionId": production_id,
            "category":     item["cat"],
            "description":  item["desc"],
            "amount":       amount,
            "expenseDate":  expense_date.isoformat() + "T00:00:00Z",
            "isQualifying": item["q"],
        }
        if item.get("vendor"):
            create_data["vendorName"] = item["vendor"]

        expense = await prisma.expense.create(data=create_data)
        created.append(expense)

    total   = sum(e.amount for e in created)
    qualify = sum(e.amount for e in created if e.isQualifying)

    logger.info(
        f"Generated {len(created)} expenses for production {production_id} "
        f"(total ${total:,.0f}, qualifying ${qualify:,.0f})"
    )
    await _trigger_budget_analysis(production_id)

    return {
        "created": len(created),
        "totalAmount": total,
        "qualifyingAmount": qualify,
        "nonQualifyingAmount": total - qualify,
        "expenses": created,
    }



@router.patch("/productions/{production_id}/expenses/{expense_id}", summary="Update an expense line item")
async def update_expense(production_id: str, expense_id: str, data: dict):
    """Update an individual expense line item — amount, description, qualifying status, vendor."""
    expense = await prisma.expense.find_unique(where={"id": expense_id})
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")
    if expense.productionId != production_id:
        raise HTTPException(status_code=403, detail="Expense does not belong to this production")

    update_data = {}
    if "description" in data:
        update_data["description"] = data["description"]
    if "amount" in data:
        update_data["amount"] = float(data["amount"])
    if "isQualifying" in data:
        update_data["isQualifying"] = bool(data["isQualifying"])
    if "vendorName" in data:
        update_data["vendorName"] = data["vendorName"]
    if "category" in data:
        update_data["category"] = data["category"]

    if not update_data:
        raise HTTPException(status_code=400, detail="No valid fields to update")

    updated = await prisma.expense.update(
        where={"id": expense_id},
        data=update_data,
    )
    await _trigger_budget_analysis(production_id)
    return updated


@router.post("/productions/{production_id}/expenses/import-from-budget-analysis",
             status_code=status.HTTP_201_CREATED,
             summary="Import line items from a Budget Analysis report")
async def import_from_budget_analysis(production_id: str, data: BudgetImportRequest):
    """
    Pulls structured line items from Budget Analysis & Risk Management
    (a separate SceneIQ service) via its authenticated API, maps each item
    onto this app's expense categories, and creates them as Expense records
    tied to this production. Labor items are always imported as
    non-qualifying pending manual ATL/BTL review — see _CATEGORY_RULES.
    """
    prod = await prisma.production.find_unique(where={"id": production_id})
    if not prod:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Production not found")

    if not BUDGET_ANALYSIS_API_URL or not BUDGET_ANALYSIS_API_KEY:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Budget Analysis integration is not configured. Set BUDGET_ANALYSIS_API_URL and BUDGET_ANALYSIS_API_KEY."
        )

    url = f"{BUDGET_ANALYSIS_API_URL.rstrip('/')}/api/budget/{data.budget_analysis_id}/line-items"
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url, headers={"X-API-Key": BUDGET_ANALYSIS_API_KEY})
    except httpx.RequestError as e:
        logger.error(f"Budget Analysis request failed: {e}")
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "Could not reach Budget Analysis service.")

    if resp.status_code == 404:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Budget analysis not found on Budget Analysis service.")
    if resp.status_code != 200:
        logger.error(f"Budget Analysis returned {resp.status_code}: {resp.text[:300]}")
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "Budget Analysis service returned an unexpected response.")

    payload = resp.json()
    line_items = payload.get("line_items", [])
    if not line_items:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "That budget analysis has no line items to import.")

    created = []
    labor_flagged = 0
    for item in line_items:
        raw_category = str(item.get("category") or "")
        raw_department = str(item.get("department") or "")
        amount = float(item.get("amount") or 0)
        if amount <= 0:
            continue

        mapped_category, is_qualifying, note = _classify_line_item(raw_category, raw_department)
        if mapped_category == "labor":
            labor_flagged += 1

        description = str(item.get("description") or raw_category or "Imported line item")

        create_data: dict = {
            "productionId": production_id,
            "category": mapped_category,
            "description": description,
            "amount": amount,
            "expenseDate": date.today().isoformat() + "T00:00:00Z",
            "isQualifying": is_qualifying,
            "qualifyingNote": note,
            "source": "budget_analysis_import",
        }
        expense = await prisma.expense.create(data=create_data)
        created.append(expense)

    total = sum(e.amount for e in created)
    qualify = sum(e.amount for e in created if e.isQualifying)

    logger.info(
    await _trigger_budget_analysis(production_id)
        f"Imported {len(created)} expenses from Budget Analysis id={data.budget_analysis_id} "
        f"into production {production_id} (total ${total:,.0f}, qualifying ${qualify:,.0f}, "
        f"{labor_flagged} labor item(s) flagged for review)"
    )

    return {
        "created": len(created),
        "totalAmount": total,
        "qualifyingAmount": qualify,
        "nonQualifyingAmount": total - qualify,
        "laborItemsFlaggedForReview": labor_flagged,
        "expenses": created,
    }


