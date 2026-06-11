# =============================================================================
# src/services/production_schedule/bridge/compliance_bridge.py
# Compliance Bridge â€” pure compute layer between the production schedule
# engine and the SceneIQ compliance stack (Incentive Calculator + MMB
# Connector).
#
# All three functions are pure: they take in-memory lists / dicts and
# return data structures the Phase 10 router can hand to the
# calculator, the reconciliation view, or the dashboard. No Prisma
# calls live here â€” the router does the DB I/O on both sides.
#
# Public functions:
#   push_shoot_days_to_calculator(production_id, jurisdiction_records)
#       Filters to verified records, returns a calculator-ready dict.
#   reconcile_with_mmb(production_id, jurisdiction_records, mmb_data)
#       Compares stripboard shoot-day counts with MMB spend-day counts
#       and produces a per-jurisdiction variance report.
#   get_compliance_data_summary(production_id, jurisdiction_records,
#                               mmb_data=None, credit_estimates=None)
#       Combined dashboard view per jurisdiction â€” shoot days, spend,
#       estimated credit, verification timestamp. Missing downstream
#       data renders as None, never raises.
# =============================================================================


# Returns the calculator-ready payload for a production:
#   {jurisdiction_id: {"shoot_days": int, "verified_at": datetime}}
#
# Only records where verified_at is not None are included â€” the brief
# is explicit that the calculator must not see unverified counts.
# `production_id` is kept on the signature for the Phase 10 router
# contract (the router loads records by production_id before calling).
def push_shoot_days_to_calculator(production_id, jurisdiction_records):
    out = {}
    for rec in jurisdiction_records:
        if rec.verified_at is None:
            continue
        out[rec.jurisdiction_id] = {
            "shoot_days":  rec.shoot_days,
            "verified_at": rec.verified_at,
        }
    return out


# Compares stripboard shoot-day counts against MMB spend-day counts
# and returns a list of per-jurisdiction reconciliation rows:
#
#   [
#       {
#           "jurisdiction":               str,
#           "shoot_days_from_stripboard": int,   # 0 if absent from records
#           "spend_days_from_mmb":        int,   # 0 if absent from mmb_data
#           "match":                      bool,  # variance == 0
#           "variance":                   int,   # abs(stripboard - mmb)
#       },
#       ...
#   ]
#
# Output covers the UNION of jurisdictions in either source so the
# reconciliation view surfaces anomalies in both directions
# (stripboard-only and MMB-only). Output ORDER is stable: records
# first (in their list order), then MMB-only jurisdictions appended
# in their dict-iteration order.
def reconcile_with_mmb(production_id, jurisdiction_records, mmb_data):
    mmb_data = mmb_data or {}

    # Index records by jurisdiction_id for O(1) lookup; preserve input
    # order via a separate list of jids.
    record_by_jid = {}
    record_order = []
    for rec in jurisdiction_records:
        if rec.jurisdiction_id not in record_by_jid:
            record_order.append(rec.jurisdiction_id)
        record_by_jid[rec.jurisdiction_id] = rec

    rows = []
    seen = set()

    for jid in record_order:
        rec = record_by_jid[jid]
        stripboard_days = rec.shoot_days
        mmb_entry = mmb_data.get(jid) or {}
        mmb_days = mmb_entry.get("spend_days", 0) or 0
        rows.append(_reconcile_row(jid, stripboard_days, mmb_days))
        seen.add(jid)

    # MMB-only jurisdictions â€” production didn't shoot here, but MMB
    # has spend recorded. Worth flagging via match=False / variance>0.
    for jid, mmb_entry in mmb_data.items():
        if jid in seen:
            continue
        mmb_days = (mmb_entry or {}).get("spend_days", 0) or 0
        rows.append(_reconcile_row(jid, 0, mmb_days))

    return rows


# Returns the combined dashboard summary:
#
#   {
#       jurisdiction_id: {
#           "shoot_days":       int,
#           "verified_at":      datetime | None,
#           "qualified_spend":  float | None,    # from mmb_data
#           "estimated_credit": float | None,    # from credit_estimates
#       },
#       ...
#   }
#
# Iterates over `jurisdiction_records` only â€” anomaly cases where MMB
# or estimates have data for jurisdictions the production didn't shoot
# in are surfaced by reconcile_with_mmb, not here.
#
# Missing or None downstream data renders as None. The function never
# raises when mmb_data or credit_estimates is missing/empty.
def get_compliance_data_summary(
    production_id,
    jurisdiction_records,
    mmb_data=None,
    credit_estimates=None,
):
    mmb_data = mmb_data or {}
    credit_estimates = credit_estimates or {}

    out = {}
    for rec in jurisdiction_records:
        jid = rec.jurisdiction_id
        mmb_entry = mmb_data.get(jid) or {}
        out[jid] = {
            "shoot_days":       rec.shoot_days,
            "verified_at":      rec.verified_at,
            "qualified_spend":  mmb_entry.get("qualified_spend"),
            "estimated_credit": credit_estimates.get(jid),
        }
    return out


# -----------------------------------------------------------------------------
# Private helpers
# -----------------------------------------------------------------------------


# Builds one reconciliation row. Pulled out so the union-merge logic
# above stays focused on iteration, not arithmetic.
def _reconcile_row(jurisdiction, stripboard_days, mmb_days):
    variance = abs(stripboard_days - mmb_days)
    return {
        "jurisdiction":               jurisdiction,
        "shoot_days_from_stripboard": stripboard_days,
        "spend_days_from_mmb":        mmb_days,
        "match":                      variance == 0,
        "variance":                   variance,
    }

