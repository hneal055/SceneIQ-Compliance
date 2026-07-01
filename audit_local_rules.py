"""
Local Rules Audit Script
-------------------------
Scans the /local-rules API across all jurisdictions and flags:
  1. Rules missing a sourceUrl (can't verify currency)
  2. Rules with a stale effectiveDate (older than STALE_YEARS)
  3. Jurisdictions with zero active local rules (missing city/county coverage)

Usage:
  1. Fill in BASE_URL, ADMIN_EMAIL, ADMIN_PASSWORD below (or set as env vars)
  2. python audit_local_rules.py
  3. Review the printed report and/or the generated CSV: local_rules_audit.csv

Note: credentials are read from environment variables so they are never
hardcoded in the file itself. Set them before running, e.g. in PowerShell:

  $env:SCENEIQ_ADMIN_EMAIL = "admin@sceneiq.com"
  $env:SCENEIQ_ADMIN_PASSWORD = "SceneIQ2026Admin"
  python audit_local_rules.py
"""

import os
import sys
import csv
from datetime import datetime, timezone

import requests

# ── Config ────────────────────────────────────────────────────────────

BASE_URL = os.environ.get("SCENEIQ_BASE_URL", "https://compliance.getsceneiq.com")
ADMIN_EMAIL = os.environ.get("SCENEIQ_ADMIN_EMAIL")
ADMIN_PASSWORD = os.environ.get("SCENEIQ_ADMIN_PASSWORD")
STALE_YEARS = 3  # flag rules with effectiveDate older than this many years
OUTPUT_CSV = "local_rules_audit.csv"


def die(msg: str):
    print(f"ERROR: {msg}")
    sys.exit(1)


def login() -> str:
    if not ADMIN_EMAIL or not ADMIN_PASSWORD:
        die(
            "Missing credentials. Set SCENEIQ_ADMIN_EMAIL and SCENEIQ_ADMIN_PASSWORD "
            "environment variables before running this script."
        )
    resp = requests.post(
        f"{BASE_URL}/api/0.1.0/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
        timeout=15,
    )
    if not resp.ok:
        die(f"Login failed ({resp.status_code}): {resp.text}")
    token = resp.json().get("access_token")
    if not token:
        die("Login succeeded but no access_token in response.")
    return token


def get_jurisdictions(token: str) -> list:
    resp = requests.get(
        f"{BASE_URL}/api/0.1.0/jurisdictions",
        headers={"Authorization": f"Bearer {token}"},
        params={"limit": 5000},
        timeout=15,
    )
    if not resp.ok:
        die(f"Failed to fetch jurisdictions ({resp.status_code}): {resp.text}")
    data = resp.json()
    return data.get("jurisdictions", data)


def get_all_local_rules(token: str) -> list:
    """Fetch ALL local rules directly in one call, rather than looping by
    jurisdiction code. This avoids silently missing rules whose jurisdiction
    isn't present (or isn't matchable) in the top-level jurisdictions list —
    e.g. county/city-level jurisdictions like Santa Fe County, NM."""
    all_rules = []
    skip = 0
    limit = 200
    while True:
        resp = requests.get(
            f"{BASE_URL}/api/0.1.0/local-rules",
            headers={"Authorization": f"Bearer {token}"},
            params={"active_only": True, "limit": limit, "skip": skip},
            timeout=15,
        )
        if not resp.ok:
            die(f"Failed to fetch local rules ({resp.status_code}): {resp.text}")
        data = resp.json()
        batch = data.get("rules", [])
        all_rules.extend(batch)
        total = data.get("total", len(all_rules))
        skip += limit
        if skip >= total or not batch:
            break
    return all_rules


def years_since(iso_date: str) -> float:
    dt = datetime.fromisoformat(iso_date.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - dt).days / 365.25


def main():
    print(f"Connecting to {BASE_URL} ...")
    token = login()

    print("Fetching jurisdictions...")
    jurisdictions = get_jurisdictions(token)
    jur_by_id = {j.get("id"): j for j in jurisdictions}
    print(f"Found {len(jurisdictions)} jurisdictions.")

    print("Fetching all local rules...")
    rules = get_all_local_rules(token)
    print(f"Found {len(rules)} active local rules.\n")

    missing_source_url = []
    stale_effective_date = []
    orphaned_rules = []  # rule references a jurisdictionId not in the jurisdictions list
    covered_jurisdiction_ids = set()
    csv_rows = []

    for rule in rules:
        jur_id = rule.get("jurisdictionId")
        jur = jur_by_id.get(jur_id)
        jur_code = jur.get("code") if jur else None
        jur_name = jur.get("name") if jur else "UNKNOWN / not in jurisdictions list"

        if jur is None:
            orphaned_rules.append((jur_id, rule.get("name"), rule.get("code")))
        else:
            covered_jurisdiction_ids.add(jur_id)

        row = {
            "jurisdiction_code": jur_code,
            "jurisdiction_name": jur_name,
            "jurisdiction_id": jur_id,
            "rule_name": rule.get("name"),
            "rule_code": rule.get("code"),
            "category": rule.get("category"),
            "effectiveDate": rule.get("effectiveDate"),
            "sourceUrl": rule.get("sourceUrl"),
            "active": rule.get("active"),
            "flag_missing_source": "",
            "flag_stale_date": "",
            "flag_orphaned": "YES" if jur is None else "",
        }

        if not rule.get("sourceUrl"):
            missing_source_url.append((jur_code or jur_id, rule.get("name"), rule.get("code")))
            row["flag_missing_source"] = "YES"

        eff_date = rule.get("effectiveDate")
        if eff_date:
            try:
                age = years_since(eff_date)
                if age > STALE_YEARS:
                    stale_effective_date.append(
                        (jur_code or jur_id, rule.get("name"), rule.get("code"), eff_date, round(age, 1))
                    )
                    row["flag_stale_date"] = f"{round(age, 1)}y old"
            except ValueError:
                row["flag_stale_date"] = "unparseable date"

        csv_rows.append(row)

    zero_coverage_jurisdictions = [
        (j.get("code"), j.get("name"))
        for j in jurisdictions
        if j.get("id") not in covered_jurisdiction_ids
    ]

    # ── Write CSV ────────────────────────────────────────────────────
    if csv_rows:
        with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(csv_rows[0].keys()))
            writer.writeheader()
            writer.writerows(csv_rows)
        print(f"Full data written to {OUTPUT_CSV}\n")

    # ── Report ───────────────────────────────────────────────────────
    print("=" * 70)
    print("LOCAL RULES AUDIT REPORT")
    print("=" * 70)

    if orphaned_rules:
        print(f"\n[!] Rules whose jurisdictionId has NO match in /jurisdictions ({len(orphaned_rules)}):")
        print("    (this means the rule's parent jurisdiction — likely a county/city —")
        print("     isn't present in the top-level jurisdictions list at all)")
        for jur_id, name, code in orphaned_rules:
            print(f"    - jurisdictionId={jur_id} | {name} ({code})")

    print(f"\n[1] Jurisdictions with ZERO active local rules ({len(zero_coverage_jurisdictions)}):")
    if zero_coverage_jurisdictions:
        for code, name in zero_coverage_jurisdictions:
            print(f"    - {code}: {name}")
    else:
        print("    None. Every jurisdiction has at least one local rule.")

    print(f"\n[2] Rules missing a sourceUrl ({len(missing_source_url)}):")
    if missing_source_url:
        for code, name, rule_code in missing_source_url:
            print(f"    - [{code}] {name} ({rule_code})")
    else:
        print("    None. Every rule has a source link.")

    print(f"\n[3] Rules with effectiveDate older than {STALE_YEARS} years ({len(stale_effective_date)}):")
    if stale_effective_date:
        for code, name, rule_code, eff_date, age in stale_effective_date:
            print(f"    - [{code}] {name} ({rule_code}) — effective {eff_date} ({age}y ago)")
    else:
        print("    None. All rules have recent effective dates.")

    print("\n" + "=" * 70)
    print(f"Total rules reviewed: {len(csv_rows)}")
    print(f"See {OUTPUT_CSV} for the full row-by-row breakdown.")
    print("=" * 70)


if __name__ == "__main__":
    main()
