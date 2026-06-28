"""
Compliance Checklist API â€” per-production requirement tracking.
"""
import logging
from typing import Optional
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from src.utils.database import prisma

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Compliance"])

# â”€â”€ Standard checklist items generated for every production â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

_STANDARD_ITEMS: list[dict] = [
    # Registration
    {"label": "Production entity registered and in good standing in the jurisdiction", "category": "registration"},
    {"label": "General liability and worker's compensation insurance obtained",         "category": "registration"},
    {"label": "Signed production commitment / letter of intent on file",               "category": "registration"},
    # Budget
    {"label": "Qualifying expense tracking system and chart of accounts established",  "category": "budget"},
    {"label": "Qualifying vs. non-qualifying expense classification confirmed with CPA","category": "budget"},
    # Documentation
    {"label": "Initial tax incentive application / certification filed with film office","category": "documentation"},
    {"label": "Daily production reports (call sheets, shooting logs) maintained",       "category": "documentation"},
    {"label": "All qualified vendor invoices collected, categorized, and filed",        "category": "documentation"},
    {"label": "Cast and crew wage records and signed payroll registers on file",        "category": "documentation"},
    {"label": "Vendor residency / jurisdiction registration documentation collected",   "category": "documentation"},
    # Audit
    {"label": "CPA-certified production audit commissioned",                            "category": "audit"},
    {"label": "Final cost report prepared and reviewed by production accountant",       "category": "audit"},
    {"label": "Tax incentive credit application submitted to film office",              "category": "audit"},
]


# â”€â”€ Pydantic models â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class ItemCreate(BaseModel):
    label:    str
    category: str = "general"
    notes:    Optional[str] = None
    dueDate:  Optional[str] = None


class ItemUpdate(BaseModel):
    status:    Optional[str] = None   # pending | complete | waived | na
    notes:     Optional[str] = None
    label:     Optional[str] = None
    category:  Optional[str] = None
    dueDate:   Optional[str] = None


# â”€â”€ Routes â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@router.get("/productions/{production_id}/compliance", summary="List compliance checklist")
async def list_compliance(production_id: str):
    prod = await prisma.production.find_unique(where={"id": production_id})
    if not prod:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Production not found")

    items = await prisma.complianceItem.find_many(
        where={"productionId": production_id},
        order=[{"category": "asc"}, {"createdAt": "asc"}],
    )
    total    = len(items)
    complete = sum(1 for i in items if i.status == "complete")
    return {
        "total":      total,
        "complete":   complete,
        "pending":    sum(1 for i in items if i.status == "pending"),
        "waived":     sum(1 for i in items if i.status == "waived"),
        "pct":        round((complete / total * 100) if total else 0, 1),
        "items":      items,
    }


@router.post("/productions/{production_id}/compliance/generate",
             status_code=status.HTTP_201_CREATED,
             summary="Auto-generate checklist from jurisdiction rules")
async def generate_checklist(production_id: str):
    """
    Delete the existing checklist for this production and regenerate it
    from the standard template plus jurisdiction-specific rule items.
    """
    prod = await prisma.production.find_unique(where={"id": production_id})
    if not prod:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Production not found")

    # Wipe existing items
    await prisma.complianceItem.delete_many(where={"productionId": production_id})

    items_to_create = list(_STANDARD_ITEMS)

    # Add rule-specific items
    if prod.jurisdictionId:
        rules = await prisma.incentiverule.find_many(
            where={"jurisdictionId": prod.jurisdictionId, "active": True}
        )
        for rule in rules:
            if rule.minSpend:
                items_to_create.append({
                    "label":    f"Minimum qualifying spend of ${rule.minSpend:,.0f} achieved for {rule.ruleName}",
                    "category": "budget",
                })
            if rule.eligibleExpenses:
                cats = ", ".join(rule.eligibleExpenses[:5])
                items_to_create.append({
                    "label":    f"Eligible expense documentation collected for {rule.ruleName} ({cats})",
                    "category": "documentation",
                })

    created = []
    for item in items_to_create:
        created.append(await prisma.complianceItem.create(data={
            "productionId": production_id,
            "label":        item["label"],
            "category":     item["category"],
        }))

    logger.info(f"Generated {len(created)} compliance items for production {production_id}")
    return {"created": len(created), "items": created}


@router.post("/productions/{production_id}/compliance",
             status_code=status.HTTP_201_CREATED,
             summary="Add a manual compliance item")
async def add_item(production_id: str, data: ItemCreate):
    prod = await prisma.production.find_unique(where={"id": production_id})
    if not prod:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Production not found")

    create_data: dict = {
        "productionId": production_id,
        "label":        data.label,
        "category":     data.category,
    }
    if data.notes:
        create_data["notes"] = data.notes
    if data.dueDate:
        create_data["dueDate"] = datetime.fromisoformat(data.dueDate).replace(tzinfo=timezone.utc)

    item = await prisma.complianceItem.create(data=create_data)
    return item


@router.patch("/compliance/{item_id}", summary="Update compliance item status or notes")
async def update_item(item_id: str, data: ItemUpdate):
    existing = await prisma.complianceItem.find_unique(where={"id": item_id})
    if not existing:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Compliance item not found")

    update: dict = {}
    if data.status is not None:
        update["status"] = data.status
        if data.status == "complete" and not existing.completedAt:
            update["completedAt"] = datetime.now(timezone.utc)
        elif data.status != "complete":
            update["completedAt"] = None
    if data.notes    is not None: update["notes"]    = data.notes
    if data.label    is not None: update["label"]    = data.label
    if data.category is not None: update["category"] = data.category
    if data.dueDate  is not None:
        update["dueDate"] = datetime.fromisoformat(data.dueDate).replace(tzinfo=timezone.utc)

    return await prisma.complianceItem.update(where={"id": item_id}, data=update)


@router.delete("/compliance/{item_id}",
               status_code=status.HTTP_204_NO_CONTENT,
               summary="Delete a compliance item")
async def delete_item(item_id: str):
    existing = await prisma.complianceItem.find_unique(where={"id": item_id})
    if not existing:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Compliance item not found")
    await prisma.complianceItem.delete(where={"id": item_id})
    return None



