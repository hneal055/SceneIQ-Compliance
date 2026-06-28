from fastapi import APIRouter, HTTPException
from src.utils.database import prisma

router = APIRouter(tags=["Budget Analysis"])
"""
ATL/BTL budget split endpoint — appended to production_expenses.py
Add this to the bottom of src/api/production_expenses.py
"""

# ATL expense descriptions from the budget template
_ATL_DESCRIPTIONS = {
    "Director",
    "Executive Producer",
    "Lead Actor – Principal",
    "Supporting Cast",
    "Screenplay / Story Rights",
}

# POST categories that are always ATL regardless of description
_ATL_CATEGORIES = set()  # currently ATL is identified by description


@router.get("/productions/{production_id}/expenses/atl-btl-split")
async def atl_btl_split(production_id: str):
    """
    Returns ATL / BTL / POST breakdown for a production.
    Industry standard for bond/contingency calculations.
    """
    expenses = await prisma.expense.find_many(
        where={"productionId": production_id}
    )
    if not expenses:
        raise HTTPException(status_code=404, detail="No expenses found for this production")

    atl, btl, post = [], [], []

    for e in expenses:
        if e.description in _ATL_DESCRIPTIONS:
            atl.append(e)
        elif e.category == "post_production":
            post.append(e)
        else:
            btl.append(e)

    atl_total  = sum(e.amount for e in atl)
    btl_total  = sum(e.amount for e in btl)
    post_total = sum(e.amount for e in post)
    grand_total = atl_total + btl_total + post_total

    # Bond/contingency base = ATL + BTL + POST (industry standard)
    contingency_base  = atl_total + btl_total + post_total
    contingency_10pct = round(contingency_base * 0.10, 2)

    return {
        "productionId": production_id,
        "atl": {
            "total": round(atl_total, 2),
            "percentage": round((atl_total / grand_total * 100) if grand_total else 0, 1),
            "items": [{"description": e.description, "amount": e.amount} for e in atl],
        },
        "btl": {
            "total": round(btl_total, 2),
            "percentage": round((btl_total / grand_total * 100) if grand_total else 0, 1),
            "items": [{"description": e.description, "amount": e.amount} for e in btl],
        },
        "post": {
            "total": round(post_total, 2),
            "percentage": round((post_total / grand_total * 100) if grand_total else 0, 1),
            "items": [{"description": e.description, "amount": e.amount} for e in post],
        },
        "grandTotal": round(grand_total, 2),
        "contingency": {
            "base": round(contingency_base, 2),
            "rate": 0.10,
            "amount": contingency_10pct,
            "description": "Bond contingency — 10% of ATL + BTL + POST"
        }
    }






