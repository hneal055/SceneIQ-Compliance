"""
Production-scoped expense endpoints — nested under /productions/{id}/expenses.
Matches the URL pattern expected by the frontend API client.
"""
import logging
from typing import Optional
from datetime import date, timedelta

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from src.utils.database import prisma

logger = logging.getLogger(__name__)
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


# â”€â”€ Pydantic models â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class ExpenseCreate(BaseModel):
    category:      str
    description:   str
    amount:        float
    expenseDate:   str           # ISO date string YYYY-MM-DD
    isQualifying:  bool = True
    vendorName:    Optional[str] = None
    subcategory:   Optional[str] = None
    qualifyingNote: Optional[str] = None


# â”€â”€ Routes â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

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
    }
    if data.vendorName:     create_data["vendorName"]    = data.vendorName
    if data.subcategory:    create_data["subcategory"]   = data.subcategory
    if data.qualifyingNote: create_data["qualifyingNote"] = data.qualifyingNote

    expense = await prisma.expense.create(data=create_data)
    logger.info(f"Expense created: {expense.id} for production {production_id}")
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

    # Spread dates: pre-prod 4 wks before, production 0â€“8 wks, post 8â€“14 wks after base
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
    return updated




