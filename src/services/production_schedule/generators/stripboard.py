# =============================================================================
# src/services/production_schedule/generators/stripboard.py
# Pure in-memory stripboard builder.
#
# The stripboard organises Scene objects into ShootDays â€” the schedule
# of which scenes shoot on which day. None of these functions touch the
# database; the Phase 10 router loads scenes/shoot_days from Prisma,
# calls these functions, and writes the result back.
#
# Public functions:
#   build_stripboard(scenes, shoot_days)
#       Returns the full stripboard as a dict keyed by day_number.
#   assign_scene_to_day(scene, shoot_day)
#       Mutates scene.shoot_day_id so the scene "belongs" to the day.
#   calculate_day_pages(shoot_day, scenes)
#       Sums page_count across the scenes assigned to a day.
#   reorder_scenes_in_day(shoot_day_id, scene_ids_ordered, scenes)
#       Returns a new scenes list with the day's scenes in the given order.
#   get_stripboard_summary(scenes, shoot_days)
#       Returns aggregate counts for a production's stripboard.
#
# NOTE on brief signatures:
#   reorder_scenes_in_day and get_stripboard_summary in the brief take
#   only IDs. Since Phase 5 stays in-memory (no DB layer yet â€” that
#   lives in Phase 10's router), this module extends both signatures
#   with the in-memory `scenes` / `shoot_days` lists they need to
#   operate on. The router will load those lists from the DB by
#   production_id / shoot_day_id and pass them down.
# =============================================================================


# Builds the full stripboard structure from in-memory scenes and shoot_days.
#
# Returns a dict keyed by ShootDay.day_number. Each value is a dict with:
#   "date"          â€” the shoot day's date string (or None)
#   "jurisdiction"  â€” the shoot day's jurisdiction_id (raw name string
#                     pending router-side FK resolution)
#   "scenes"        â€” the scenes assigned to that day, sorted by scene_number
#   "total_pages"   â€” sum of those scenes' page_count values (None treated as 0)
#
# Outer-dict insertion order mirrors the input shoot_days list. Scenes whose
# shoot_day_id matches no provided day are silently excluded â€” they're
# "unassigned" until the caller assigns them.
def build_stripboard(scenes, shoot_days):
    stripboard = {}

    # Group scenes by shoot_day_id in a single pass â€” cheaper than O(N*D).
    scenes_by_day_id = {}
    for scene in scenes:
        if scene.shoot_day_id is None:
            continue
        scenes_by_day_id.setdefault(scene.shoot_day_id, []).append(scene)

    for shoot_day in shoot_days:
        # Sort scenes within the day by scene_number. Lexicographic is fine
        # for the MVP â€” natural sort over mixed strings like "12A" or
        # "INSERT-3" is a future improvement, and reorder_scenes_in_day
        # lets the caller impose an explicit order when it matters.
        day_scenes = sorted(
            scenes_by_day_id.get(shoot_day.id, []),
            key=lambda s: s.scene_number or "",
        )
        total_pages = sum((s.page_count or 0.0) for s in day_scenes)

        stripboard[shoot_day.day_number] = {
            "date": shoot_day.date,
            "jurisdiction": shoot_day.jurisdiction_id,
            "scenes": day_scenes,
            "total_pages": total_pages,
        }

    return stripboard


# Links a Scene to a ShootDay by setting scene.shoot_day_id. If
# shoot_day.id is None (e.g. a fresh dataclass not yet persisted),
# scene.shoot_day_id becomes None too â€” callers should give shoot_days
# stable ids before assigning (the Phase 10 router does this by
# persisting the ShootDay first, then assigning scenes to its returned id).
def assign_scene_to_day(scene, shoot_day):
    scene.shoot_day_id = shoot_day.id


# Sums the page_count of every scene whose shoot_day_id matches the given
# shoot_day.id. Treats None page_counts as 0.0. Returns 0.0 if no scenes
# are assigned to the day.
def calculate_day_pages(shoot_day, scenes):
    total = 0.0
    for scene in scenes:
        if scene.shoot_day_id == shoot_day.id and scene.page_count is not None:
            total += scene.page_count
    return total


# Reorders the scenes belonging to one shoot day according to the supplied
# list of scene ids. Returns a NEW list (does not mutate the input).
#
# Behaviour:
#   - Scenes belonging to shoot_day_id appear in the exact order of
#     scene_ids_ordered.
#   - Any scenes belonging to shoot_day_id but NOT in scene_ids_ordered
#     are appended in their original relative order (defensive â€” caller
#     shouldn't drop scenes by omission).
#   - Scenes belonging to other shoot days, or unassigned scenes, pass
#     through in their original relative order, interleaved with the
#     reordered day's scenes at the positions where that day's scenes
#     first appeared.
#
# The simplest implementation that satisfies the test (and matches how a
# drag-and-drop frontend will use this) is:
#   1. Walk the original scenes list once, picking up the day's scenes in
#      the new order and other scenes in their original order.
def reorder_scenes_in_day(shoot_day_id, scene_ids_ordered, scenes):
    # Index the day's scenes by id so we can pull them in the desired order.
    scenes_in_day_by_id = {
        s.id: s for s in scenes if s.shoot_day_id == shoot_day_id
    }

    # Build the desired sequence for THIS DAY: requested order first, then
    # any day-scenes the caller omitted (in their original relative order).
    day_sequence = []
    seen = set()
    for sid in scene_ids_ordered:
        if sid in scenes_in_day_by_id and sid not in seen:
            day_sequence.append(scenes_in_day_by_id[sid])
            seen.add(sid)
    for s in scenes:
        if s.shoot_day_id == shoot_day_id and s.id not in seen:
            day_sequence.append(s)
            seen.add(s.id)

    # Walk the original scenes list. Each time we hit a scene belonging to
    # this day, replace it with the next from day_sequence. Other scenes
    # pass through unchanged.
    day_iter = iter(day_sequence)
    out = []
    for s in scenes:
        if s.shoot_day_id == shoot_day_id:
            out.append(next(day_iter))
        else:
            out.append(s)

    return out


# Returns aggregate counts for the stripboard:
#   total_shoot_days              â€” len(shoot_days)
#   total_scenes                  â€” len(scenes) (assigned or not)
#   total_pages                   â€” sum of page_count across all scenes
#   shoot_days_per_jurisdiction   â€” dict[jurisdiction_id, day_count]
#
# `jurisdiction_id` on each shoot_day is a raw name string in our
# in-memory pipeline (the router resolves names â†’ real FK ids before
# persisting). Days with no jurisdiction (jurisdiction_id is None) are
# grouped under the key None.
def get_stripboard_summary(scenes, shoot_days):
    total_pages = sum((s.page_count or 0.0) for s in scenes)

    by_jurisdiction = {}
    for day in shoot_days:
        key = day.jurisdiction_id
        by_jurisdiction[key] = by_jurisdiction.get(key, 0) + 1

    return {
        "total_shoot_days": len(shoot_days),
        "total_scenes": len(scenes),
        "total_pages": total_pages,
        "shoot_days_per_jurisdiction": by_jurisdiction,
    }




