"""
SceneIQ — Sub-Jurisdiction Monitor
Fetches feed URLs for county/city/town jurisdictions, detects content changes
via SHA-256 hash comparison, sends changed content to Claude for rule extraction,
and stores extracted rules as PendingRule records for human review.

Usage:
    python monitor.py                  # run all active sub-jurisdictions
    python monitor.py --code NY-ERIE   # run a single jurisdiction by code
    python monitor.py --dry-run        # fetch and hash only, no DB writes
"""

import argparse
import asyncio
import hashlib
import json
import logging
import os
import re
import sys
from datetime import datetime, timezone

import httpx
from anthropic import Anthropic
from dotenv import load_dotenv
from prisma import Json, Prisma

load_dotenv(override=True)

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("pilotforge.monitor")

# ── Claude client ─────────────────────────────────────────────────────────────
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
if not ANTHROPIC_API_KEY:
    log.error("ANTHROPIC_API_KEY not set in environment")
    sys.exit(1)

claude = Anthropic(api_key=ANTHROPIC_API_KEY)

SUB_JURISDICTION_TYPES = {"county", "city", "town", "borough", "district", "parish"}

MAX_CONTENT_CHARS = 15_000   # truncation limit sent to Claude
MAX_RAW_STORED    = 5_000    # chars stored in pending_rules.rawContent

EXTRACTION_PROMPT = """\
You are a tax incentive and compliance analyst for the film and TV production industry.

Analyze the government web page content below and extract every rule, fee, permit, \
tax, or requirement that a film or TV production company operating in this jurisdiction \
would need to know about. Focus on: filming permits, location fees, business licenses, \
payroll tax rates, sales tax exemptions, production incentives, insurance requirements, \
and any local ordinances affecting production.

Return ONLY a valid JSON object — no markdown, no explanation — matching this schema:

{
  "rules": [
    {
      "name": "Short descriptive rule name",
      "category": "permit_fee | business_license | filming_tax | wage_requirement | incentive | restriction | other",
      "rule_type": "fee | tax | requirement | restriction | credit | exemption",
      "amount": <number or null>,
      "percentage": <number or null>,
      "description": "Full description of the rule",
      "requirements": "Conditions or eligibility requirements, or null",
      "effective_date": "YYYY-MM-DD or null",
      "expiration_date": "YYYY-MM-DD or null"
    }
  ],
  "confidence": <0.0 to 1.0>,
  "summary": "One-sentence summary of what was found",
  "no_rules_found": <true | false>
}

If nothing relevant is found return:
{"rules":[],"confidence":0.0,"summary":"No production-relevant rules found","no_rules_found":true}

Content to analyze:
---
{content}
---"""


# ── Helpers ───────────────────────────────────────────────────────────────────

def _html_to_text(html: str) -> str:
    """Return whitespace-normalised visible text from an HTML string.

    Uses regex pre-stripping so malformed HTML (e.g. unclosed <head> tags)
    doesn't suppress body text.
    """
    # Remove entire <head>…</head> blocks (non-greedy, case-insensitive)
    html = re.sub(r"<head\b[^>]*>.*?</head>", "", html, flags=re.DOTALL | re.IGNORECASE)
    # Remove script / style / noscript blocks
    html = re.sub(
        r"<(script|style|noscript)\b[^>]*>.*?</\1>",
        "",
        html,
        flags=re.DOTALL | re.IGNORECASE,
    )
    # Strip remaining tags
    text = re.sub(r"<[^>]+>", " ", html)
    return re.sub(r"\s+", " ", text).strip()


async def fetch_url(url: str, timeout: int = 30) -> str | None:
    """Fetch URL and return cleaned visible text content, or None on failure."""
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=timeout) as http:
            r = await http.get(
                url,
                headers={"User-Agent": "SceneIQ-Monitor/1.0 (tax incentive compliance)"},
            )
            r.raise_for_status()
            content_type = r.headers.get("content-type", "")
            if "html" in content_type or url.endswith((".htm", ".html", ".shtml")):
                return _html_to_text(r.text)
            return r.text  # PDF / plain-text feeds pass through as-is
    except httpx.HTTPStatusError as e:
        log.warning(f"HTTP {e.response.status_code} fetching {url}")
    except Exception as e:
        log.warning(f"Failed to fetch {url}: {e}")
    return None


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def extract_json(text: str) -> dict:
    """Find and return the first balanced JSON object in text."""
    # Try the whole text first (ideal case)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Walk forward looking for a valid balanced JSON object
    start = text.find("{")
    while start != -1:
        depth = 0
        for i, ch in enumerate(text[start:], start):
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(text[start : i + 1])
                    except json.JSONDecodeError:
                        break  # try next '{'
        start = text.find("{", start + 1)

    raise ValueError(f"No valid JSON object found in Claude response: {text[:300]}")


MOCK_CLAUDE = os.getenv("MOCK_CLAUDE", "false").lower() == "true"


def call_claude(content: str) -> dict:
    """Send content to Claude and parse JSON response."""
    if MOCK_CLAUDE:
        log.info("  [MOCK] Returning simulated extraction (set MOCK_CLAUDE=false to use real API)")
        return {
            "rules": [
                {
                    "name": "Film Permit Fee",
                    "category": "permit_fee",
                    "rule_type": "fee",
                    "amount": 250.0,
                    "percentage": None,
                    "description": "Mock: standard filming permit fee for county locations",
                    "requirements": "Application 10 business days in advance",
                    "effective_date": "2026-01-01",
                    "expiration_date": None,
                }
            ],
            "confidence": 0.5,
            "summary": "Mock extraction — real Claude API not available",
            "no_rules_found": False,
        }
    truncated = content[:MAX_CONTENT_CHARS]
    prompt = EXTRACTION_PROMPT.replace("{content}", truncated)
    msg = claude.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = msg.content[0].text.strip()
    log.debug(f"Claude raw response: {raw[:500]}")
    return extract_json(raw)


# ── Core processing ───────────────────────────────────────────────────────────

async def process_jurisdiction(db: Prisma, jur, dry_run: bool = False) -> dict:
    """
    Check one jurisdiction's feed for changes.
    Returns a result dict with keys: name, changed, rules_found, skipped, error.
    """
    result = {"name": jur.name, "changed": False, "rules_found": 0, "skipped": False, "error": None}

    content = await fetch_url(jur.feedUrl)
    if content is None:
        result["error"] = "fetch_failed"
        return result

    new_hash = sha256(content)

    if jur.feedLastHash == new_hash:
        log.info(f"  [{jur.code}] No change")
        if not dry_run:
            await db.jurisdiction.update(
                where={"id": jur.id},
                data={"feedLastChecked": datetime.now(timezone.utc)},
            )
        result["skipped"] = True
        return result

    log.info(f"  [{jur.code}] Change detected — sending to Claude")
    result["changed"] = True

    if dry_run:
        log.info(f"  [{jur.code}] DRY RUN — skipping Claude call and DB write")
        return result

    try:
        extracted = call_claude(content)
    except (json.JSONDecodeError, ValueError) as e:
        log.error(f"  [{jur.code}] Claude returned invalid JSON: {e}")
        result["error"] = "claude_json_error"
        return result
    except Exception as e:
        log.error(f"  [{jur.code}] Claude API error: {type(e).__name__}: {e}")
        result["error"] = "claude_api_error"
        return result

    rule_count = len(extracted.get("rules", []))
    confidence = extracted.get("confidence", 0.0)
    log.info(f"  [{jur.code}] {rule_count} rule(s) extracted, confidence={confidence:.2f}")

    now = datetime.now(timezone.utc)

    await db.pendingrule.create(
        data={
            "jurisdiction": {"connect": {"id": jur.id}},
            "sourceUrl": jur.feedUrl,
            "rawContent": content[:MAX_RAW_STORED],
            "extractedData": Json(json.dumps(extracted)),
            "confidence": confidence,
            "status": "pending",
            "updatedAt": now,
        }
    )

    await db.jurisdiction.update(
        where={"id": jur.id},
        data={"feedLastHash": new_hash, "feedLastChecked": now},
    )

    result["rules_found"] = rule_count
    return result


async def main(code_filter: str | None = None, dry_run: bool = False):
    log.info("═" * 60)
    log.info("SceneIQ Sub-Jurisdiction Monitor")
    if dry_run:
        log.info("DRY RUN MODE — no database writes")
    log.info("═" * 60)

    db = Prisma()
    await db.connect()

    try:
        where: dict = {"active": True, "feedUrl": {"not": None}}

        if code_filter:
            where["code"] = code_filter
        else:
            where["type"] = {"in": list(SUB_JURISDICTION_TYPES)}

        jurisdictions = await db.jurisdiction.find_many(where=where)

        if not jurisdictions:
            log.warning("No matching sub-jurisdictions with feedUrl found.")
            log.warning("Run: python scripts/seed_sub_jurisdictions.py")
            return

        log.info(f"Monitoring {len(jurisdictions)} jurisdiction(s)")
        log.info("")

        totals = {"changed": 0, "skipped": 0, "errors": 0, "rules": 0}

        for jur in jurisdictions:
            log.info(f"▶ {jur.name} ({jur.code})")
            result = await process_jurisdiction(db, jur, dry_run=dry_run)

            if result["error"]:
                totals["errors"] += 1
                log.warning(f"  Error: {result['error']}")
            elif result["skipped"]:
                totals["skipped"] += 1
            else:
                totals["changed"] += 1
                totals["rules"] += result["rules_found"]

        log.info("")
        log.info("─" * 60)
        log.info(f"Complete — changed: {totals['changed']}  unchanged: {totals['skipped']}  errors: {totals['errors']}  pending rules queued: {totals['rules']}")

    finally:
        await db.disconnect()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SceneIQ Sub-Jurisdiction Monitor")
    parser.add_argument("--code",    help="Run a single jurisdiction by code (e.g. NY-ERIE)")
    parser.add_argument("--dry-run", action="store_true", help="Fetch only, no DB writes or Claude calls")
    args = parser.parse_args()

    asyncio.run(main(code_filter=args.code, dry_run=args.dry_run))
