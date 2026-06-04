"""
Throwaway: seed pending_rules with 6 demo entries across mixed statuses
so the Pending Rules Review page (sidebar: Rule Review) has content under
each filter tab (All / Pending / Approved / Rejected).

Not committed.
"""

import asyncio
import json
import sys
from datetime import datetime, timezone

sys.path.insert(0, ".")
from src.utils.database import prisma


# 6 demo rules pinned to specific jurisdiction codes so narratives match
# the displayed jurisdiction.
DEMO_RULES = [
    {
        "jurisdiction_code": "GA",
        "status": "pending",
        "confidence": 0.94,
        "source_url": "https://film.example.gov/atlanta-bonus-2026",
        "raw_content": (
            "Atlanta Metro Production Incentive — productions filming "
            "primarily within Fulton County qualify for an additional 5% "
            "transferable tax credit on qualifying expenditures above the "
            "state baseline. Effective January 1, 2026."
        ),
        "extracted": {
            "summary": "Atlanta Metro bonus credit — +5% over state baseline.",
            "rules": [
                {
                    "name": "Atlanta Metro Bonus Credit",
                    "rule_type": "credit_bonus",
                    "category": "tax_credit",
                    "percentage": 5.0,
                    "effective_date": "2026-01-01",
                    "description": "Additional 5% transferable credit for productions filming primarily in Fulton County."
                }
            ],
        },
    },
    {
        "jurisdiction_code": "NM",
        "status": "pending",
        "confidence": 0.88,
        "source_url": "https://nm.film.example/santa-fe-fee-waiver",
        "raw_content": (
            "Santa Fe Film Office permit-fee waiver program — all municipal "
            "location permits waived for productions registered with the "
            "city film office. Eligibility requires advance registration "
            "30 days before principal photography."
        ),
        "extracted": {
            "summary": "Santa Fe municipal permit-fee waiver for registered productions.",
            "rules": [
                {
                    "name": "Santa Fe Permit Fee Waiver",
                    "rule_type": "fee_waiver",
                    "category": "permit",
                    "amount": 0,
                    "effective_date": "2026-03-01",
                    "description": "Waiver of all municipal location permit fees with 30-day advance registration."
                }
            ],
        },
    },
    {
        "jurisdiction_code": "UK",
        "status": "pending",
        "confidence": 0.62,
        "source_url": "https://uk.film.example/london-borough-2026",
        "raw_content": (
            "London Borough Production Levy notice — proposed (not yet "
            "enacted) borough-level surcharge of 1.5% on productions over "
            "GBP 50M filming primarily within Greater London. Status: "
            "consultation phase; effective date TBD."
        ),
        "extracted": {
            "summary": "Proposed London borough surcharge (consultation phase).",
            "rules": [
                {
                    "name": "London Borough Production Levy (Proposed)",
                    "rule_type": "surcharge",
                    "category": "levy",
                    "percentage": 1.5,
                    "min_spend": 50000000,
                    "effective_date": None,
                    "description": "Proposed 1.5% levy on productions over £50M; consultation phase, not yet enacted."
                }
            ],
        },
    },
    {
        "jurisdiction_code": "LA",
        "status": "approved",
        "confidence": 0.97,
        "source_url": "https://la.film.example/nola-2026-update",
        "raw_content": (
            "New Orleans Film & Video local industry uplift — qualifying "
            "productions filming at least 60% of principal photography "
            "within Orleans Parish receive an additional 5% local credit "
            "on top of Louisiana state credit. Approved by city council "
            "February 2026."
        ),
        "extracted": {
            "summary": "NOLA 5% local uplift for 60%+ in-parish productions.",
            "rules": [
                {
                    "name": "New Orleans Local Production Uplift",
                    "rule_type": "credit_bonus",
                    "category": "tax_credit",
                    "percentage": 5.0,
                    "effective_date": "2026-02-01",
                    "description": "Additional 5% local credit when 60%+ of principal photography is in Orleans Parish."
                }
            ],
        },
    },
    {
        "jurisdiction_code": "OR",
        "status": "rejected",
        "confidence": 0.41,
        "source_url": "https://or.film.example/portland-rumor-feed",
        "raw_content": (
            "Tweet-aggregated report — unverified claim of a 10% Portland "
            "metro production credit. No primary source cited; appears to "
            "conflate the state credit with a city-level program that does "
            "not exist."
        ),
        "extracted": {
            "summary": "Unverified Portland 10% credit — no primary source.",
            "rules": [
                {
                    "name": "Portland Metro Production Credit (Unverified)",
                    "rule_type": "credit",
                    "category": "tax_credit",
                    "percentage": 10.0,
                    "effective_date": None,
                    "description": "Unverified claim of a 10% Portland metro credit; appears to misattribute the state credit."
                }
            ],
        },
    },
    {
        "jurisdiction_code": "ON",
        "status": "pending",
        "confidence": 0.79,
        "source_url": "https://on.film.example/toronto-stage-2026",
        "raw_content": (
            "Toronto Film, Television and Digital Media Office — new soundstage "
            "construction grant program (max grant CAD 2M per stage) for "
            "stages over 15,000 sqft built within City of Toronto between "
            "2026 and 2028. Applications open March 2026."
        ),
        "extracted": {
            "summary": "Toronto soundstage construction grant (max CAD 2M, 2026-2028).",
            "rules": [
                {
                    "name": "Toronto Soundstage Construction Grant",
                    "rule_type": "grant",
                    "category": "infrastructure",
                    "amount": 2000000,
                    "effective_date": "2026-03-15",
                    "expiration_date": "2028-12-31",
                    "description": "Up to CAD 2M grant per stage for new builds over 15,000 sqft within City of Toronto."
                }
            ],
        },
    },
]


async def main():
    await prisma.connect()
    try:
        # Look up each rule's matching jurisdiction by code so the displayed
        # jurisdiction matches the rule narrative ("Atlanta" → Georgia, etc.).
        codes = [r["jurisdiction_code"] for r in DEMO_RULES]
        jur_rows = await prisma.jurisdiction.find_many(where={"code": {"in": codes}})
        by_code = {j.code: j for j in jur_rows}
        missing = [c for c in codes if c not in by_code]
        if missing:
            print(f"ERROR: jurisdictions missing in DB: {missing}", file=sys.stderr)
            return 1

        # Wipe any prior demo seed for these jurisdictions so this script is idempotent.
        wiped = await prisma.pendingrule.delete_many(
            where={"jurisdictionId": {"in": [j.id for j in jur_rows]}}
        )
        if wiped:
            print(f"Cleared {wiped} prior pending-rule row(s) for these jurisdictions")

        now = datetime.now(timezone.utc)
        for spec in DEMO_RULES:
            j = by_code[spec["jurisdiction_code"]]
            data = {
                "jurisdictionId":  j.id,
                "sourceUrl":       spec["source_url"],
                "rawContent":      spec["raw_content"],
                "extractedData":   json.dumps(spec["extracted"]),
                "confidence":      spec["confidence"],
                "status":          spec["status"],
            }
            if spec["status"] != "pending":
                data["reviewedBy"] = "admin@sceneiq.com"
                data["reviewedAt"] = now
            await prisma.pendingrule.create(data=data)
            print(f"  + [{spec['status']:9s}] {j.code:6s} ({j.name}) conf={spec['confidence']}")

        total = await prisma.pendingrule.count()
        pending = await prisma.pendingrule.count(where={"status": "pending"})
        approved = await prisma.pendingrule.count(where={"status": "approved"})
        rejected = await prisma.pendingrule.count(where={"status": "rejected"})
        print(f"Done. pending_rules totals: total={total}, pending={pending}, approved={approved}, rejected={rejected}")
    finally:
        await prisma.disconnect()


asyncio.run(main())
