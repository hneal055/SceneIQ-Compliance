"""
Database seeding â€” jurisdictions, incentive rules.

Called from src/main.py lifespan on every startup.
All operations are idempotent: existing records are skipped by unique key.
"""
import json
import logging
from datetime import datetime

from src.utils.database import prisma

logger = logging.getLogger(__name__)


# â”€â”€ Migrations â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def run_migrations() -> None:
    """Migrations are handled externally via scripts/resolve_migrations.py in the startCommand."""
    logger.info("â„¹ï¸  Migrations handled externally â€” skipping")


# â”€â”€ Jurisdiction data (22 total) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

_JURISDICTIONS = [
    # Core USA
    {"name": "California",      "code": "CA", "country": "USA",            "type": "state",    "description": "California Film & TV Tax Credit Program",                 "website": "https://film.ca.gov/tax-credit/",                                                                                     "active": True},
    {"name": "Georgia",         "code": "GA", "country": "USA",            "type": "state",    "description": "Georgia Film Tax Credit Program",                         "website": "https://www.georgia.org/film",                                                                                        "active": True},
    {"name": "New York",        "code": "NY", "country": "USA",            "type": "state",    "description": "New York Film Production Tax Credit",                     "website": "https://esd.ny.gov/nyc-film-tv-commercials-production-credit",                                                        "active": True},
    {"name": "Louisiana",       "code": "LA", "country": "USA",            "type": "state",    "description": "Louisiana Motion Picture Production Tax Credit",           "website": "https://www.louisianaentertainment.gov/film/",                                                                        "active": True},
    {"name": "New Mexico",      "code": "NM", "country": "USA",            "type": "state",    "description": "New Mexico Film Production Tax Credit",                   "website": "https://www.nmfilm.com/incentives/",                                                                                  "active": True},
    # Extended USA
    {"name": "Michigan",        "code": "MI", "country": "USA",            "type": "state",    "description": "Michigan Film Production Incentive",                      "website": "https://www.michiganbusiness.org/industries/film/",                                                                    "active": True},
    {"name": "New Jersey",      "code": "NJ", "country": "USA",            "type": "state",    "description": "NJ Film Tax Credit Program",                              "website": "https://www.njeda.gov/film/",                                                                                         "active": True},
    {"name": "Virginia",        "code": "VA", "country": "USA",            "type": "state",    "description": "Virginia Film Tax Credit",                                "website": "https://www.film.virginia.gov/incentives/",                                                                           "active": True},
    {"name": "Colorado",        "code": "CO", "country": "USA",            "type": "state",    "description": "Colorado Film Incentive Program",                         "website": "https://coloradofilm.org/incentives/",                                                                                "active": True},
    {"name": "Hawaii",          "code": "HI", "country": "USA",            "type": "state",    "description": "Hawaii Film Production Tax Credit",                       "website": "https://filmoffice.hawaii.gov/tax-incentive/",                                                                        "active": True},
    {"name": "Oregon",          "code": "OR", "country": "USA",            "type": "state",    "description": "Oregon Production Investment Fund",                       "website": "https://www.oregon4biz.com/Film/",                                                                                    "active": True},
    {"name": "Montana",         "code": "MT", "country": "USA",            "type": "state",    "description": "Montana Media Production Tax Credit",                     "website": "https://montanafilm.com/incentive-program/",                                                                          "active": True},
    {"name": "Mississippi",     "code": "MS", "country": "USA",            "type": "state",    "description": "Mississippi Film Incentive Program",                      "website": "https://www.filmmississippi.org/incentives",                                                                          "active": True},
    {"name": "Illinois",        "code": "IL", "country": "USA",            "type": "state",    "description": "Illinois Film Services Tax Credit - 30% base credit",    "website": "https://www.commerce.illinois.gov/industries/film-office",                                                            "active": True},
    # Canada
    {"name": "British Columbia","code": "BC", "country": "Canada",         "type": "province", "description": "BC Film Incentive & Production Services Tax Credit",      "website": "https://creativebc.com/programs-funding/production-incentives/",                                                      "active": True},
    {"name": "Ontario",         "code": "ON", "country": "Canada",         "type": "province", "description": "Ontario Film & Television Tax Credit",                   "website": "https://ontariocreates.ca/tax-incentives/",                                                                           "active": True},
    {"name": "Quebec",          "code": "QC", "country": "Canada",         "type": "province", "description": "Quebec Film Production Tax Credit",                      "website": "https://www.sodec.gouv.qc.ca/en/programs/",                                                                           "active": True},
    # International
    {"name": "United Kingdom",  "code": "UK", "country": "United Kingdom", "type": "country",  "description": "UK Film Tax Relief & High-End TV Tax Relief",            "website": "https://www.bfi.org.uk/certification-funding/british-certification-tax-relief",                                       "active": True},
    {"name": "Australia",       "code": "AU", "country": "Australia",      "type": "country",  "description": "Australian Screen Production Incentive",                  "website": "https://www.screenaustralia.gov.au/funding-and-support/producer-offset",                                             "active": True},
    {"name": "Ireland",         "code": "IE", "country": "Ireland",        "type": "country",  "description": "Section 481 Film Tax Credit - 32% credit",               "website": "https://www.revenue.ie/en/companies-and-charities/reliefs-and-exemptions/film-relief/index.aspx",                   "active": True},
    {"name": "France",          "code": "FR", "country": "France",         "type": "country",  "description": "French Tax Rebate for International Production (TRIP) - 30%", "website": "https://www.cnc.fr/professionnels/aides-et-financements/",                                                    "active": True},
    {"name": "Spain",           "code": "ES", "country": "Spain",          "type": "country",  "description": "Spanish Film Production Incentives - 30% rebate",         "website": "https://www.icex.es/",                                                                                               "active": True},
    {"name": "New Zealand",     "code": "NZ", "country": "New Zealand",    "type": "country",  "description": "NZ Screen Production Grant - 40% rebate",                 "website": "https://www.nzfilm.co.nz/funding/nzspg",                                                                             "active": True},
]


# â”€â”€ Incentive rules data (33 total) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

_RULES = [
    # California
    {"jurisdictionCode": "CA", "ruleName": "California Film & TV Tax Credit 2.0",       "ruleCode": "CA-FILM-2.0",     "incentiveType": "tax_credit", "percentage": 20.0, "minSpend": 1000000, "maxCredit": 10000000, "eligibleExpenses": ["labor", "equipment", "locations", "post_production"],                    "excludedExpenses": ["above_the_line", "marketing", "financing_costs"], "effectiveDate": datetime(2024, 1, 1), "requirements": {"minShootDays": 10, "californiaResidents": 75, "relocatingProject": False}, "active": True},
    {"jurisdictionCode": "CA", "ruleName": "California Relocating TV Series Credit",     "ruleCode": "CA-TV-RELOCATE",  "incentiveType": "tax_credit", "percentage": 25.0, "minSpend": 1000000, "maxCredit": 12000000, "eligibleExpenses": ["labor", "equipment", "locations", "post_production"],                    "excludedExpenses": ["above_the_line", "marketing"],                    "effectiveDate": datetime(2024, 1, 1), "requirements": {"relocatingProject": True, "tvSeries": True, "californiaResidents": 75},  "active": True},
    # Georgia
    {"jurisdictionCode": "GA", "ruleName": "Georgia Film Tax Credit",                    "ruleCode": "GA-FILM-BASE",    "incentiveType": "tax_credit", "percentage": 20.0, "minSpend": 500000,                         "eligibleExpenses": ["labor", "equipment", "locations", "post_production", "talent"],         "excludedExpenses": ["marketing", "distribution"],                      "effectiveDate": datetime(2024, 1, 1), "requirements": {"georgiaSpend": 500000, "promotionalRequirements": True},                 "active": True},
    {"jurisdictionCode": "GA", "ruleName": "Georgia Film Tax Credit + Promotional Bonus","ruleCode": "GA-FILM-PROMO",   "incentiveType": "tax_credit", "percentage": 30.0, "minSpend": 500000,                         "eligibleExpenses": ["labor", "equipment", "locations", "post_production", "talent"],         "excludedExpenses": ["marketing", "distribution"],                      "effectiveDate": datetime(2024, 1, 1), "requirements": {"georgiaSpend": 500000, "georgiaPromo": True, "logoInCredits": True},     "active": True},
    # New York
    {"jurisdictionCode": "NY", "ruleName": "NY Film Production Tax Credit",              "ruleCode": "NY-FILM-BASE",    "incentiveType": "tax_credit", "percentage": 30.0, "minSpend": 250000,  "maxCredit": 7000000,  "eligibleExpenses": ["labor", "equipment", "locations", "post_production"],                    "excludedExpenses": ["above_the_line_over_cap", "marketing"],           "effectiveDate": datetime(2024, 1, 1), "requirements": {"nySpend": 75, "shootingDays": 75},                                       "active": True},
    {"jurisdictionCode": "NY", "ruleName": "NY Post-Production Credit",                  "ruleCode": "NY-POST-PROD",    "incentiveType": "tax_credit", "percentage": 30.0, "minSpend": 250000,  "maxCredit": 7000000,  "eligibleExpenses": ["post_production", "vfx", "editing", "sound"],                          "excludedExpenses": ["marketing"],                                      "effectiveDate": datetime(2024, 1, 1), "requirements": {"nyFacilities": True},                                                    "active": True},
    # Louisiana
    {"jurisdictionCode": "LA", "ruleName": "Louisiana Film Tax Credit",                  "ruleCode": "LA-FILM-BASE",    "incentiveType": "tax_credit", "percentage": 25.0, "minSpend": 300000,                         "eligibleExpenses": ["labor", "equipment", "locations", "post_production"],                    "excludedExpenses": ["marketing", "above_the_line_over_1m"],            "effectiveDate": datetime(2024, 1, 1), "requirements": {"louisianaResident": 60, "louisianaSpend": 300000},                      "active": True},
    {"jurisdictionCode": "LA", "ruleName": "Louisiana Additional Payroll Credit",        "ruleCode": "LA-PAYROLL-BONUS","incentiveType": "tax_credit", "percentage": 10.0,                                             "eligibleExpenses": ["louisiana_resident_labor"],                                             "excludedExpenses": [],                                                 "effectiveDate": datetime(2024, 1, 1), "requirements": {"louisianaResident": 100, "stackableWithBase": True},                     "active": True},
    # New Mexico
    {"jurisdictionCode": "NM", "ruleName": "New Mexico Film Production Tax Credit",      "ruleCode": "NM-FILM-BASE",    "incentiveType": "tax_credit", "percentage": 25.0, "minSpend": 50000,                          "eligibleExpenses": ["labor", "equipment", "locations", "post_production"],                    "excludedExpenses": ["marketing", "indirect_costs"],                    "effectiveDate": datetime(2024, 1, 1), "requirements": {"newMexicoSpend": 60},                                                    "active": True},
    {"jurisdictionCode": "NM", "ruleName": "New Mexico Veteran Crew Bonus",              "ruleCode": "NM-VETERAN-BONUS","incentiveType": "tax_credit", "percentage": 5.0,                                              "eligibleExpenses": ["veteran_labor"],                                                        "excludedExpenses": [],                                                 "effectiveDate": datetime(2024, 1, 1), "requirements": {"veteranCrew": True, "stackableWithBase": True},                          "active": True},
    # British Columbia
    {"jurisdictionCode": "BC", "ruleName": "BC Film Incentive - Basic",                  "ruleCode": "BC-FILM-BASIC",   "incentiveType": "tax_credit", "percentage": 35.0,                                             "eligibleExpenses": ["bc_labor"],                                                             "excludedExpenses": ["non_bc_labor", "marketing"],                      "effectiveDate": datetime(2024, 1, 1), "requirements": {"bcResident": True, "canadianContent": True},                             "active": True},
    {"jurisdictionCode": "BC", "ruleName": "BC Production Services Tax Credit",          "ruleCode": "BC-PSTC",         "incentiveType": "tax_credit", "percentage": 28.0,                                             "eligibleExpenses": ["bc_labor", "bc_goods_services"],                                        "excludedExpenses": ["marketing", "financing"],                         "effectiveDate": datetime(2024, 1, 1), "requirements": {"foreignProduction": True, "bcSpend": 1000000},                           "active": True},
    # Ontario
    {"jurisdictionCode": "ON", "ruleName": "Ontario Film & Television Tax Credit",       "ruleCode": "ON-FILM-BASE",    "incentiveType": "tax_credit", "percentage": 35.0,                                             "eligibleExpenses": ["ontario_labor"],                                                        "excludedExpenses": ["marketing", "financing"],                         "effectiveDate": datetime(2024, 1, 1), "requirements": {"ontarioResident": True, "canadianContent": True},                        "active": True},
    {"jurisdictionCode": "ON", "ruleName": "Ontario Production Services Tax Credit",     "ruleCode": "ON-PSTC",         "incentiveType": "tax_credit", "percentage": 21.5,                                             "eligibleExpenses": ["ontario_labor"],                                                        "excludedExpenses": ["marketing"],                                      "effectiveDate": datetime(2024, 1, 1), "requirements": {"foreignProduction": True},                                                "active": True},
    # Quebec
    {"jurisdictionCode": "QC", "ruleName": "Quebec Film Production Tax Credit",          "ruleCode": "QC-FILM-BASE",    "incentiveType": "tax_credit", "percentage": 40.0,                                             "eligibleExpenses": ["quebec_labor"],                                                         "excludedExpenses": ["marketing", "above_the_line"],                    "effectiveDate": datetime(2024, 1, 1), "requirements": {"quebecResident": True, "frenchLanguage": 75},                            "active": True},
    # United Kingdom
    {"jurisdictionCode": "UK", "ruleName": "UK Film Tax Relief",                         "ruleCode": "UK-FILM-BASE",    "incentiveType": "tax_credit", "percentage": 25.0, "minSpend": 1000000,                        "eligibleExpenses": ["uk_core_expenditure"],                                                  "excludedExpenses": ["marketing", "distribution"],                      "effectiveDate": datetime(2024, 1, 1), "requirements": {"ukSpend": 10, "culturalTest": True, "ukProduction": True},               "active": True},
    # Michigan
    {"jurisdictionCode": "MI", "ruleName": "Michigan Film Production Incentive",         "ruleCode": "MI-FILM-BASE",    "incentiveType": "rebate",     "percentage": 30.0, "minSpend": 50000,                          "eligibleExpenses": ["labor", "goods", "services", "michigan_spend"],                         "excludedExpenses": ["marketing", "distribution"],                      "effectiveDate": datetime(2024, 1, 1), "requirements": {"michiganSpend": 50000, "completionWithin12Months": True},                "active": True},
    # New Jersey
    {"jurisdictionCode": "NJ", "ruleName": "NJ Film Tax Credit",                         "ruleCode": "NJ-FILM-BASE",    "incentiveType": "tax_credit", "percentage": 30.0, "minSpend": 1000000,                        "eligibleExpenses": ["labor", "services", "goods"],                                           "excludedExpenses": ["above_the_line_over_500k", "marketing"],          "effectiveDate": datetime(2024, 1, 1), "requirements": {"njSpend": 60, "diversity": True},                                        "active": True},
    {"jurisdictionCode": "NJ", "ruleName": "NJ Film Tax Credit - Diversity Bonus",       "ruleCode": "NJ-DIVERSITY",    "incentiveType": "tax_credit", "percentage": 5.0,                                              "eligibleExpenses": ["qualified_diverse_spend"],                                              "excludedExpenses": [],                                                 "effectiveDate": datetime(2024, 1, 1), "requirements": {"diversityPlan": True, "stackableWithBase": True},                        "active": True},
    # Virginia
    {"jurisdictionCode": "VA", "ruleName": "Virginia Film Tax Credit",                   "ruleCode": "VA-FILM-BASE",    "incentiveType": "tax_credit", "percentage": 20.0, "minSpend": 250000,  "maxCredit": 6500000,  "eligibleExpenses": ["virginia_labor", "goods", "services"],                                 "excludedExpenses": ["marketing"],                                      "effectiveDate": datetime(2024, 1, 1), "requirements": {"virginiaSpend": 250000},                                                  "active": True},
    {"jurisdictionCode": "VA", "ruleName": "Virginia Enhanced Credit - Rural",           "ruleCode": "VA-RURAL",        "incentiveType": "tax_credit", "percentage": 10.0,                                             "eligibleExpenses": ["rural_spend"],                                                          "excludedExpenses": [],                                                 "effectiveDate": datetime(2024, 1, 1), "requirements": {"ruralLocation": True, "stackableWithBase": True},                        "active": True},
    # Colorado
    {"jurisdictionCode": "CO", "ruleName": "Colorado Film Incentive",                    "ruleCode": "CO-FILM-BASE",    "incentiveType": "rebate",     "percentage": 20.0, "minSpend": 100000,                         "eligibleExpenses": ["colorado_labor", "colorado_goods"],                                     "excludedExpenses": ["marketing", "distribution"],                      "effectiveDate": datetime(2024, 1, 1), "requirements": {"coloradoSpend": 100000},                                                  "active": True},
    # Hawaii
    {"jurisdictionCode": "HI", "ruleName": "Hawaii Film Production Tax Credit",          "ruleCode": "HI-FILM-BASE",    "incentiveType": "tax_credit", "percentage": 20.0, "minSpend": 200000,                         "eligibleExpenses": ["hawaii_labor", "goods", "services"],                                    "excludedExpenses": ["marketing"],                                      "effectiveDate": datetime(2024, 1, 1), "requirements": {"hawaiiResident": 50, "hawaiiSpend": 200000},                            "active": True},
    {"jurisdictionCode": "HI", "ruleName": "Hawaii Additional Credit - Neighbor Islands","ruleCode": "HI-NEIGHBOR",     "incentiveType": "tax_credit", "percentage": 5.0,                                              "eligibleExpenses": ["neighbor_island_spend"],                                                "excludedExpenses": [],                                                 "effectiveDate": datetime(2024, 1, 1), "requirements": {"neighborIsland": True, "stackableWithBase": True},                       "active": True},
    # Oregon
    {"jurisdictionCode": "OR", "ruleName": "Oregon Production Investment Fund",          "ruleCode": "OR-OPIF",         "incentiveType": "rebate",     "percentage": 20.0, "minSpend": 750000,  "maxCredit": 10000000, "eligibleExpenses": ["oregon_labor", "oregon_goods"],                                         "excludedExpenses": ["marketing"],                                      "effectiveDate": datetime(2024, 1, 1), "requirements": {"oregonLabor": 50, "oregonSpend": 750000},                               "active": True},
    # Montana
    {"jurisdictionCode": "MT", "ruleName": "Montana Media Production Tax Credit",        "ruleCode": "MT-FILM-BASE",    "incentiveType": "tax_credit", "percentage": 35.0, "minSpend": 50000,                          "eligibleExpenses": ["montana_labor", "montana_goods"],                                       "excludedExpenses": ["marketing", "distribution"],                      "effectiveDate": datetime(2024, 1, 1), "requirements": {"montanaSpend": 50000},                                                    "active": True},
    # Mississippi
    {"jurisdictionCode": "MS", "ruleName": "Mississippi Film Incentive - Base",          "ruleCode": "MS-FILM-BASE",    "incentiveType": "rebate",     "percentage": 25.0, "minSpend": 50000,                          "eligibleExpenses": ["mississippi_labor", "goods", "services"],                               "excludedExpenses": ["marketing"],                                      "effectiveDate": datetime(2024, 1, 1), "requirements": {"mississippiSpend": 50000},                                               "active": True},
    {"jurisdictionCode": "MS", "ruleName": "Mississippi Payroll Bonus",                  "ruleCode": "MS-PAYROLL",      "incentiveType": "rebate",     "percentage": 10.0,                                             "eligibleExpenses": ["mississippi_resident_labor"],                                           "excludedExpenses": [],                                                 "effectiveDate": datetime(2024, 1, 1), "requirements": {"mississippiResident": 100, "stackableWithBase": True},                   "active": True},
    # Illinois
    {"jurisdictionCode": "IL", "ruleName": "Illinois Film Services Tax Credit",          "ruleCode": "IL-FILM-BASE",    "incentiveType": "tax_credit", "percentage": 30.0, "minSpend": 100000,                         "eligibleExpenses": ["labor", "goods", "services", "illinois_spend"],                         "excludedExpenses": ["marketing", "distribution"],                      "effectiveDate": datetime(2024, 1, 1), "requirements": {"illinoisSpend": 100000, "illinoisResident": 60},                        "active": True},
    {"jurisdictionCode": "IL", "ruleName": "Illinois Chicago Location Bonus",            "ruleCode": "IL-CHICAGO-BONUS","incentiveType": "tax_credit", "percentage": 15.0,                                             "eligibleExpenses": ["chicago_spend"],                                                        "excludedExpenses": [],                                                 "effectiveDate": datetime(2024, 1, 1), "requirements": {"chicagoLocation": True, "stackableWithBase": True},                      "active": True},
    # Ireland
    {"jurisdictionCode": "IE", "ruleName": "Section 481 Film Tax Credit",                "ruleCode": "IE-S481",         "incentiveType": "tax_credit", "percentage": 32.0,                                             "eligibleExpenses": ["irish_labor", "irish_goods"],                                           "excludedExpenses": ["marketing", "distribution"],                      "effectiveDate": datetime(2024, 1, 1), "requirements": {"irishSpend": 250000, "culturalTest": True},                              "active": True},
    # France
    {"jurisdictionCode": "FR", "ruleName": "Tax Rebate for International Production (TRIP)", "ruleCode": "FR-TRIP",     "incentiveType": "rebate",     "percentage": 30.0, "minSpend": 1000000, "maxCredit": 30000000, "eligibleExpenses": ["french_eligible_spend"],                                                 "excludedExpenses": ["development", "marketing"],                       "effectiveDate": datetime(2024, 1, 1), "requirements": {"minFrenchSpend": 1000000, "culturalTest": True},                        "active": True},
    # Spain
    {"jurisdictionCode": "ES", "ruleName": "Spanish Film Production Incentive",          "ruleCode": "ES-FILM",         "incentiveType": "rebate",     "percentage": 30.0, "minSpend": 1000000,                        "eligibleExpenses": ["spanish_eligible_spend"],                                               "excludedExpenses": ["marketing", "distribution"],                      "effectiveDate": datetime(2024, 1, 1), "requirements": {"spanishSpend": 1000000, "culturalTest": True},                          "active": True},
    # New Zealand
    {"jurisdictionCode": "NZ", "ruleName": "NZ Screen Production Grant",                 "ruleCode": "NZ-NZSPG",        "incentiveType": "grant",      "percentage": 40.0, "minSpend": 15000000,                       "eligibleExpenses": ["nz_labor", "nz_goods_services"],                                        "excludedExpenses": ["marketing", "distribution"],                      "effectiveDate": datetime(2024, 1, 1), "requirements": {"nzSpend": 15000000, "significantNZContent": True},                     "active": True},
    {"jurisdictionCode": "NZ", "ruleName": "NZ Post-Digital-Visual Effects Grant",       "ruleCode": "NZ-PDV",          "incentiveType": "grant",      "percentage": 20.0, "minSpend": 500000,                         "eligibleExpenses": ["nz_vfx", "nz_post_production"],                                         "excludedExpenses": [],                                                 "effectiveDate": datetime(2024, 1, 1), "requirements": {"nzPDVSpend": 500000},                                                    "active": True},
]


# â”€â”€ Seed functions (assume prisma is already connected) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

async def _seed_jurisdictions() -> None:
    existing = await prisma.jurisdiction.find_many()
    existing_codes = {j.code for j in existing}
    added = 0
    for jur in _JURISDICTIONS:
        if jur["code"] not in existing_codes:
            await prisma.jurisdiction.create(data=jur)
            added += 1
    if added:
        logger.info(f"âœ… Seeded {added} jurisdictions")
    else:
        logger.info("â„¹ï¸  Jurisdictions already seeded â€” skipping")


async def _seed_rules() -> None:
    jurisdictions = await prisma.jurisdiction.find_many()
    jur_map = {j.code: j.id for j in jurisdictions}

    existing_rules = await prisma.incentiverule.find_many()
    existing_codes = {r.ruleCode for r in existing_rules}

    added = 0
    for rule in _RULES:
        rule = dict(rule)  # don't mutate module-level data
        jur_code = rule.pop("jurisdictionCode")
        if jur_code not in jur_map or rule["ruleCode"] in existing_codes:
            continue
        if "requirements" in rule:
            rule["requirements"] = json.dumps(rule["requirements"])
        await prisma.incentiverule.create(
            data={**rule, "jurisdiction": {"connect": {"id": jur_map[jur_code]}}}
        )
        added += 1

    if added:
        logger.info(f"âœ… Seeded {added} incentive rules")
    else:
        logger.info("â„¹ï¸  Incentive rules already seeded â€” skipping")


# â”€â”€ Demo productions â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

_DEMO_PRODUCTIONS = [
    {
        "title":            "The Silent Horizon",
        "productionType":   "feature",
        "jurisdictionCode": "GA",
        "budgetTotal":      15000000.0,
        "budgetQualifying": 12750000.0,
        "status":           "production",
        "productionCompany":"Horizon Pictures",
        "startDate":        datetime(2026, 1, 15),
    },
    {
        "title":            "Echoes of Midnight",
        "productionType":   "tv_series",
        "jurisdictionCode": "NY",
        "budgetTotal":      8000000.0,
        "budgetQualifying": 6400000.0,
        "status":           "pre_production",
        "productionCompany":"Midnight Studios",
        "startDate":        datetime(2026, 3, 1),
    },
    {
        "title":            "Neon Pulse",
        "productionType":   "feature",
        "jurisdictionCode": "CA",
        "budgetTotal":      4500000.0,
        "budgetQualifying": 3600000.0,
        "status":           "planning",
        "productionCompany":"SceneIQ Studios",
        "startDate":        datetime(2026, 6, 1),
    },
]


async def _seed_productions() -> None:
    existing = await prisma.production.find_many()
    existing_titles = {p.title for p in existing}

    jurisdictions = await prisma.jurisdiction.find_many()
    jur_map = {j.code: j.id for j in jurisdictions}

    added = 0
    for prod in _DEMO_PRODUCTIONS:
        if prod["title"] in existing_titles:
            continue
        jur_code = prod["jurisdictionCode"]
        if jur_code not in jur_map:
            continue
        data = {k: v for k, v in prod.items() if k != "jurisdictionCode"}
        data["jurisdictionId"] = jur_map[jur_code]
        await prisma.production.create(data=data)
        added += 1

    if added:
        logger.info(f"âœ… Seeded {added} demo productions")
    else:
        logger.info("â„¹ï¸  Demo productions already seeded â€” skipping")


_DEMO_MONITORING_SOURCES = [
    {
        "name": "California Film Commission",
        "url": "https://film.ca.gov/",
        "feedUrl": None,
        "sourceType": "web",
        "jurisdiction": "CA",
    },
    {
        "name": "British Film Commission",
        "url": "https://britishfilmcommission.org.uk/",
        "feedUrl": None,
        "sourceType": "web",
        "jurisdiction": "UK",
    },
    {
        "name": "Georgia Dept. of Economic Development",
        "url": "https://www.georgia.org/film",
        "feedUrl": None,
        "sourceType": "web",
        "jurisdiction": "GA",
    },
    # Sources with live RSS feeds for ingestion
    {
        "name": "UK Government â€” Film & TV Tax Relief News",
        "url": "https://www.gov.uk/topic/business-tax/creative-industry-tax-reliefs",
        "feedUrl": "https://www.gov.uk/search/news-and-communications.atom?keywords=film+tax+relief&order=updated-newest",
        "sourceType": "atom",
        "jurisdiction": "UK",
    },
    {
        "name": "Variety â€” Business & Finance",
        "url": "https://variety.com/v/biz/",
        "feedUrl": "https://variety.com/v/biz/feed/",
        "sourceType": "rss",
        "jurisdiction": None,
    },
    {
        "name": "Deadline â€” Business",
        "url": "https://deadline.com/category/business/",
        "feedUrl": "https://deadline.com/category/business/feed/",
        "sourceType": "rss",
        "jurisdiction": None,
    },
]

_DEMO_MONITORING_EVENTS = [
    {
        "sourceName": "California Film Commission",
        "title": "Studio Zone Expansion Under Review",
        "summary": "Proposed expansion of the 30-mile studio zone currently under committee review.",
        "url": "https://film.ca.gov/tax-credit/",
        "severity": "info",
        "publishedAt": datetime(2026, 3, 25, 10, 0, 0),
    },
    {
        "sourceName": "British Film Commission",
        "title": "VFX Expenditure Guidance Updated",
        "summary": "New guidance issued for VFX expenditure qualification under the High-End TV and Film Tax Relief updates.",
        "url": "https://britishfilmcommission.org.uk/",
        "severity": "warning",
        "publishedAt": datetime(2026, 3, 25, 7, 30, 0),
    },
    {
        "sourceName": "Georgia Dept. of Economic Development",
        "title": "FY Cap Status: 65% Utilized",
        "summary": "Fiscal year cap status: 65% utilized. Applications remain open â€” plan submissions accordingly.",
        "url": "https://www.georgia.org/film",
        "severity": "info",
        "publishedAt": datetime(2026, 3, 24, 9, 0, 0),
    },
]


async def _seed_monitoring() -> None:
    """Seed demo monitoring sources and events. Idempotent â€” skips if sources already exist."""
    existing = await prisma.monitoringsource.find_many()
    existing_names = {s.name for s in existing}

    source_map: dict[str, str] = {s.name: s.id for s in existing}
    added_sources = 0
    for src in _DEMO_MONITORING_SOURCES:
        if src["name"] in existing_names:
            continue
        record = await prisma.monitoringsource.create(data={"id": str(__import__("uuid").uuid4()), "updatedAt": __import__("datetime").datetime.utcnow(), 
            "name": src["name"],
            "url": src["url"],
            "feedUrl": src.get("feedUrl"),
            "sourceType": src["sourceType"],
            "jurisdiction": src.get("jurisdiction"),
        })
        source_map[record.name] = record.id
        added_sources += 1

    # Seed events (skip if any events already exist for this source)
    added_events = 0
    for ev in _DEMO_MONITORING_EVENTS:
        src_id = source_map.get(ev["sourceName"])
        if not src_id:
            continue
        existing_ev = await prisma.monitoringevent.find_first(where={"sourceId": src_id})
        if existing_ev:
            continue
        await prisma.monitoringevent.create(data={
            "sourceId": src_id,
            "title": ev["title"],
            "summary": ev["summary"],
            "url": ev["url"],
            "severity": ev["severity"],
            "publishedAt": ev["publishedAt"],
        })
        added_events += 1

    if added_sources or added_events:
        logger.info(f"âœ… Seeded {added_sources} monitoring sources, {added_events} events")
    else:
        logger.info("â„¹ï¸  Monitoring data already seeded â€” skipping")


async def seed_all() -> None:
    """Seed jurisdictions, incentive rules, demo productions, and monitoring data. Idempotent â€” safe on every startup."""
    await _seed_jurisdictions()
    await _seed_rules()
    await _seed_productions()
    await _seed_monitoring()







