# =============================================================================
# ADD TO: src/services/production_schedule/config/field_maps.py
# Append this block after MMS_FIELD_MAP
# =============================================================================

# Final Draft element type constants
# Used by fdx_importer.py to identify paragraph types
FDX_ELEMENT_TYPES = {
    "scene_heading" : "Scene Heading",
    "action"        : "Action",
    "character"     : "Character",
    "dialogue"      : "Dialogue",
    "transition"    : "Transition",
    "parenthetical" : "Parenthetical",
    "shot"          : "Shot",
    "general"       : "General",
}

# Parenthetical suffixes to strip from character names
FDX_CHARACTER_PARENTHETICALS = [
    "(V.O.)",       # Voice over
    "(O.S.)",       # Off screen
    "(O.C.)",       # Off camera
    "(CONT'D)",     # Continued
    "(PRE-LAP)",    # Pre-lap audio
]

