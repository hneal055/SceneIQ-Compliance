import sys
import os
import json

sys.path.insert(0, 'backend')
from app.db.session import SessionLocal
from app.models.program import Program

# Correct, clean JSON structure
corrected_rules = {
    "program_name": "Georgia Film Tax Credit",
    "jurisdiction": "Georgia",
    "version": "2025.01",
    "base_credit_rate": 0.20,
    "bonus_conditions": [
        {
            "id": "promotional_logo",
            "name": "Georgia Promotional Logo",
            "rate": 0.10,
            "condition": "logo_included == True",
            "description": "Additional 10% for including the Georgia state logo in credits"
        }
    ],
    "qualified_expenditure_categories": [
        "above_the_line",
        "below_the_line",
        "post_production",
        "visual_effects",
        "music_production",
        "transportation",
        "lodging"
    ],
    "minimum_requirements": [
        {
            "id": "min_spend",
            "rule": "qualified_spend >= 500000",
            "message": "Minimum qualified spend of $500,000 required",
            "severity": "blocking"
        },
        {
            "id": "georgia_filming",
            "rule": "filming_location contains 'Georgia'",
            "message": "At least 50% of principal photography must occur in Georgia",
            "severity": "blocking"
        }
    ],
    "exclusions": [
        {
            "category": "music_licensing",
            "condition": "licensor_resident_georgia == False",
            "message": "Music licensing payments to non-Georgia residents are excluded"
        }
    ],
    "local_hire_bonus": {
        "rate": 0.05,
        "threshold": 0.15,
        "description": "Additional 5% when Georgia resident crew exceeds 15% of total crew"
    },
    "diversity_bonus": {
        "rate": 0.02,
        "threshold": 0.20,
        "description": "Additional 2% for diversity in key creative roles"
    },
    "application_deadlines": {
        "initial_application": {
            "timing": "within 90 days of principal photography commencement",
            "message": "Initial application must be filed within 90 days"
        },
        "final_claim": {
            "timing": "within 3 years of completion",
            "message": "Final claim must be submitted within 3 years"
        }
    },
    "checklist": [
        {"item": "Register with Georgia Film Office", "required": True},
        {"item": "Submit GEIPA form", "required": True},
        {"item": "Provide affidavit of Georgia spend", "required": True},
        {"item": "Confirm promotional logo inclusion", "required": False, "condition": "logo_included == True"}
    ],
    "transferability": {
        "allowed": True,
        "fee_market_range": "0.88 - 0.94 per dollar"
    },
    "sunset_date": "2028-12-31"
}

db = SessionLocal()
try:
    program = db.query(Program).filter(Program.name == "Georgia Film Tax Credit").first()
    if program:
        program.rules = json.dumps(corrected_rules, indent=2)
        db.commit()
        print("✅ Georgia rules updated with correct JSON structure.")
        print(f"Program ID: {program.id}")
        print(f"Base credit rate: {corrected_rules['base_credit_rate']*100}%")
    else:
        print("❌ Program not found. Run seed_georgia.py first.")
except Exception as e:
    print(f"Error: {e}")
    db.rollback()
finally:
    db.close()
