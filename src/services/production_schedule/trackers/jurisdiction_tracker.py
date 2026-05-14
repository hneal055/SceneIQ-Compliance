# =============================================================================
# src/services/production_schedule/trackers/jurisdiction_tracker.py
# Jurisdiction Shoot Day Tracker.
#
# Aggregates shoot-day counts by jurisdiction so the Phase 9
# ComplianceBridge can hand verified counts to the existing Incentive
# Calculator. All three functions stay pure in-memory; the Phase 10
# router will own the Prisma upsert / update_many calls.
#
# Public functions:
#   count_shoot_days_per_jurisdiction(production_id, shoot_days)
#       Returns {jurisdiction_id: count} for an in-memory shoot-day list.
#   get_jurisdiction_summary(production_id, records, jurisdictions=None)
#       Returns a dashboard-shaped list of dicts from JurisdictionShootDays
#       records, optionally resolving jurisdiction names from a lookup.
#   verify_shoot_days(production_id, records, *, now=None)
#       Sets verified_at on each record. Used when a user clicks "Verify"
#       in the dashboard.
# =============================================================================

from datetime import datetime, timezone


# Counts how many ShootDays fall under each jurisdiction for a
# production. Days whose `jurisdiction_id is None` are excluded —
# they haven't been assigned to a jurisdiction yet and including them
# would arbitrarily inflate one bucket.
#
# `production_id` is unused inside the function but kept on the
# signature for the Phase 10 router contract (the router will pass
# it along to `upsert(...)` after receiving the dict).
def count_shoot_days_per_jurisdiction(production_id, shoot_days):
    counts = {}
    for day in shoot_days:
        jid = day.jurisdiction_id
        if jid is None:
            continue
        counts[jid] = counts.get(jid, 0) + 1
    return counts


# Returns a dashboard-shaped list of jurisdiction summaries:
#
#   [
#       {
#           "jurisdiction_id":   str,
#           "jurisdiction_name": str,         # resolved via `jurisdictions` lookup
#                                              # or falls back to jurisdiction_id
#           "shoot_days":        int,
#           "verified_at":       datetime | None,
#       },
#       ...
#   ]
#
# `records` is a list of JurisdictionShootDays dataclass objects (or
# anything with .jurisdiction_id / .shoot_days / .verified_at).
#
# `jurisdictions` is an optional list of objects exposing .id and .name;
# the function builds a {.id -> .name} lookup so the summary can show
# human-readable names. When the lookup is absent or doesn't contain a
# match, `jurisdiction_name` falls back to `jurisdiction_id` — which in
# our in-memory pipeline is a raw name string anyway (the Phase 10
# router resolves names to real Jurisdiction.id FKs at persist time).
#
# Output order matches the input `records` order.
def get_jurisdiction_summary(production_id, records, jurisdictions=None):
    name_lookup = {}
    if jurisdictions:
        for j in jurisdictions:
            name_lookup[j.id] = getattr(j, "name", None)

    summary = []
    for rec in records:
        resolved_name = name_lookup.get(rec.jurisdiction_id)
        summary.append(
            {
                "jurisdiction_id":   rec.jurisdiction_id,
                "jurisdiction_name": resolved_name or rec.jurisdiction_id,
                "shoot_days":        rec.shoot_days,
                "verified_at":       rec.verified_at,
            }
        )
    return summary


# Marks every record's verified_at as `now` (defaults to UTC now).
# Mutates each record AND returns the list — same idiom as
# assign_scene_to_day in the stripboard module.
#
# `now` is injectable so tests can pin a deterministic timestamp.
def verify_shoot_days(production_id, records, *, now=None):
    timestamp = now if now is not None else datetime.now(timezone.utc)
    for rec in records:
        rec.verified_at = timestamp
    return records
