"""
SceneIQ Database Setup Script
Creates database, runs migrations, and seeds initial data
"""
import asyncio
from datetime import datetime
from prisma import Prisma

# Jurisdiction and Rule data
JURISDICTIONS = [
    {"name": "California", "code": "CA", "country": "United States", "type": "state"},
    {"name": "Georgia", "code": "GA", "country": "United States", "type": "state"},
    {"name": "Louisiana", "code": "LA", "country": "United States", "type": "state"},
    {"name": "New Mexico", "code": "NM", "country": "United States", "type": "state"},
    {"name": "New York", "code": "NY", "country": "United States", "type": "state"},
    {"name": "Texas", "code": "TX", "country": "United States", "type": "state"},
    {"name": "Florida", "code": "FL", "country": "United States", "type": "state"},
    {"name": "British Columbia", "code": "BC", "country": "Canada", "type": "province"},
    {"name": "Ontario", "code": "ON", "country": "Canada", "type": "province"},
    {"name": "Quebec", "code": "QC", "country": "Canada", "type": "province"},
    {"name": "United Kingdom", "code": "UK", "country": "United Kingdom", "type": "country"},
]

INCENTIVE_RULES = [
    {"jurisdiction_code": "BC", "ruleName": "BC Film Incentive", "ruleCode": "BC-FI-BASIC", "incentiveType": "tax_credit", "percentage": 35.0, "minSpend": 100000.0, "eligibleExpenses": ["labour"], "excludedExpenses": ["financing"]},
    {"jurisdiction_code": "CA", "ruleName": "California Film Tax Credit", "ruleCode": "CA-FTTC", "incentiveType": "tax_credit", "percentage": 20.0, "minSpend": 1000000.0, "maxCredit": 20000000.0, "eligibleExpenses": ["qualified_wages"], "excludedExpenses": ["marketing"]},
    {"jurisdiction_code": "GA", "ruleName": "Georgia Film Tax Credit", "ruleCode": "GA-FTC", "incentiveType": "tax_credit", "percentage": 20.0, "minSpend": 500000.0, "eligibleExpenses": ["all_production"], "excludedExpenses": []},
    {"jurisdiction_code": "LA", "ruleName": "Louisiana Motion Picture Tax Credit", "ruleCode": "LA-MPTC", "incentiveType": "tax_credit", "percentage": 25.0, "minSpend": 300000.0, "eligibleExpenses": ["in_state_expenditures"], "excludedExpenses": ["marketing"]},
    {"jurisdiction_code": "NY", "ruleName": "New York Film Production Tax Credit", "ruleCode": "NY-FPTC", "incentiveType": "tax_credit", "percentage": 30.0, "minSpend": 250000.0, "eligibleExpenses": ["qualified_production_costs"], "excludedExpenses": ["marketing"]},
]

async def setup():
    print("ðŸŽ¬ SceneIQ Database Setup")
    print("=" * 50)
    prisma = Prisma()
    await prisma.connect()
    try:
        print("\nðŸ“ Creating jurisdictions...")
        jurisdiction_map = {}
        for jur_data in JURISDICTIONS:
            jur = await prisma.jurisdiction.create(data={"name": jur_data["name"], "code": jur_data["code"], "country": jur_data["country"], "type": jur_data["type"], "active": True})
            jurisdiction_map[jur.code] = jur.id
            print(f"  âœ“ {jur.name} ({jur.code})")
        print(f"âœ… Created {len(JURISDICTIONS)} jurisdictions\n")
        print("ðŸ“‹ Creating incentive rules...")
        for rule_data in INCENTIVE_RULES:
            jurisdiction_id = jurisdiction_map.get(rule_data["jurisdiction_code"])
            if not jurisdiction_id:
                continue
            await prisma.incentiverule.create(data={"jurisdictionId": jurisdiction_id, "ruleName": rule_data["ruleName"], "ruleCode": rule_data["ruleCode"], "incentiveType": rule_data["incentiveType"], "percentage": rule_data.get("percentage"), "minSpend": rule_data.get("minSpend"), "maxCredit": rule_data.get("maxCredit"), "eligibleExpenses": rule_data["eligibleExpenses"], "excludedExpenses": rule_data["excludedExpenses"], "effectiveDate": datetime.now(), "active": True})
            print(f"  âœ“ {rule_data['ruleName']}")
        print(f"âœ… Created {len(INCENTIVE_RULES)} incentive rules\n")
        print("=" * 50)
        print("âœ… Setup complete! SceneIQ is ready!")
    finally:
        await prisma.disconnect()

if __name__ == "__main__":
    asyncio.run(setup())

