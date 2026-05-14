# =============================================================================
# src/services/production_schedule/config/field_maps.py
# Header→field maps for script-breakdown importers.
#
# Add new header variants on the LEFT as you encounter them in real-world
# script-breakdown exports. The RIGHT-hand value is the internal field name
# on the Scene dataclass at src/services/production_schedule/models/scene.py.
#
# Pattern mirrors src/services/broadcast_scheduler/config/field_maps.py:
# case-sensitive exact match, leading/trailing whitespace stripped by the
# importer before lookup.
# =============================================================================


# Maps real-world script-breakdown CSV column headers → internal Scene
# field names. The importer normalises header whitespace before lookup,
# so "Scene Number" and " Scene Number " both match.
CSV_SCENE_FIELD_MAP = {
    # Scene number
    "Scene Number"      : "scene_number",
    "Scene #"           : "scene_number",
    "Scene No"          : "scene_number",
    "Scene No."         : "scene_number",

    # Title / slugline
    "Scene Title"       : "title",
    "Title"             : "title",
    "Slugline"          : "title",

    # Location
    "Location"          : "location",
    "Set"               : "location",
    "Setting"           : "location",

    # Int / Ext
    "Int/Ext"           : "location_type",
    "INT/EXT"           : "location_type",
    "I/E"               : "location_type",

    # Day / Night / Dawn / Dusk
    "Day/Night"         : "time_of_day",
    "Time"              : "time_of_day",
    "TOD"               : "time_of_day",

    # Page count (decimal pages — 8/8 = 1.0)
    "Page Count"        : "page_count",
    "Pages"             : "page_count",
    "Eighths"           : "page_count",

    # Cast / characters appearing in the scene
    "Cast"              : "cast_ids",
    "Characters"        : "cast_ids",
    "Cast List"         : "cast_ids",

    # Jurisdiction — stored as a raw name on Scene.jurisdiction_id by the
    # importer; the router resolves name → Jurisdiction.id at persist time.
    "Jurisdiction"      : "jurisdiction_name",
    "Location State"    : "jurisdiction_name",
    "State"             : "jurisdiction_name",

    # Free-text notes
    "Notes"             : "notes",
    "Comments"          : "notes",
    "Production Notes"  : "notes",
}


# Maps Movie Magic Scheduling .mms (XML) tag names → internal Scene
# field names. Two sentinel values trigger specialised parsers in
# mms_importer.py:
#   "scene_heading" → _parse_scene_heading()  (splits "INT. X - DAY"
#                     into loc_type / location / time_of_day)
#   "cast"          → _extract_cast()         (flattens xmltodict's
#                     str / dict / list shapes into a list[str])
MMS_FIELD_MAP = {
    # Scene identification
    "SceneNumber"       : "scene_number",
    "SceneNum"          : "scene_number",
    "Number"            : "scene_number",
    "StripNumber"       : "scene_number",

    # Scene heading — parsed separately by _parse_scene_heading()
    "SceneHeading"      : "scene_heading",
    "Heading"           : "scene_heading",
    "SlugLine"          : "scene_heading",
    "Header"            : "scene_heading",

    # Scene title / description
    "Description"       : "title",
    "SceneDescription"  : "title",
    "Title"             : "title",
    "Synopsis"          : "title",

    # Location
    "SetName"           : "location",
    "Location"          : "location",
    "Set"               : "location",

    # Page count — converted to float by build_scene_from_mms_element()
    "PageCount"         : "page_count",
    "Pages"             : "page_count",
    "PageLength"        : "page_count",
    "Eighths"           : "page_count",

    # Cast / elements — split into list by _extract_cast()
    "ElementList"       : "cast",
    "Characters"        : "cast",
    "Cast"              : "cast",
    "Talent"            : "cast",

    # Jurisdiction hint (raw name — resolved to FK in router)
    "ShootDay"          : "jurisdiction_id",
    "Location_State"    : "jurisdiction_id",
    "State"             : "jurisdiction_id",

    # Notes
    "Notes"             : "notes",
    "SceneNotes"        : "notes",

    # -------------------------------------------------------------------------
    # Intentionally NOT mapped — these tags are silently ignored:
    # ProductionNote, DirectorNote, CameraNote, BudgetCode, ColorCode
    # -------------------------------------------------------------------------
}
