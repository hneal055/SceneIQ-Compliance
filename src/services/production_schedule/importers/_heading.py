# =============================================================================
# src/services/production_schedule/importers/_heading.py
# Shared scene-heading parser used by both the MMS and FDX importers.
#
# Parses a script-style scene heading like "INT. POLICE STATION - DAY"
# into a (loc_type, location, time_of_day) triple. The output values are
# canonicalised so downstream code never has to second-guess casing or
# alternate spellings.
#
# Lifted out of mms_importer.py in Phase 4 so fdx_importer.py can share
# it. Leading-underscore module name signals: private to the importers
# package â€” callers outside this package should not import it directly.
# =============================================================================


# Parses a scene heading like "INT. POLICE STATION - DAY" into
# (loc_type, location, time_of_day). Returns (None, None, None) for
# headings we can't make sense of â€” never raises.
#
# Recognises:
#   loc_type    : INT, EXT, INT/EXT, EXT/INT, I/E
#   time_of_day : DAY, NIGHT, DAWN, DUSK, MORNING, EVENING, CONTINUOUS
def parse_scene_heading_text(text):
    if not text:
        return (None, None, None)

    # Collapse runs of whitespace and uppercase for token matching.
    upper = " ".join(text.upper().split())

    # Split into head ("INT. POLICE STATION") and tail ("DAY").
    # Prefer " - " (with surrounding spaces); fall back to the last "-"
    # only when the trailing token is a recognised time-of-day word, so
    # locations like "POLICE STATION - INTERROGATION" don't get chopped.
    head_part = upper
    tail_part = ""
    if " - " in upper:
        head_part, _, tail_part = upper.partition(" - ")
    elif "-" in upper:
        last_dash = upper.rfind("-")
        candidate_tail = upper[last_dash + 1:].strip()
        if candidate_tail in _TIME_TOKENS:
            head_part = upper[:last_dash]
            tail_part = candidate_tail

    head_part = head_part.strip().rstrip(".").strip()
    tail_part = tail_part.strip().rstrip(".").strip()

    # Pull the loc_type token off the front of head_part. Order matters:
    # compound tokens (INT/EXT, EXT/INT, I/E) are tried before bare INT/EXT.
    loc_type = None
    location = None
    for token in _LOC_TYPE_TOKENS:
        if (
            head_part == token
            or head_part.startswith(token + " ")
            or head_part.startswith(token + ".")
        ):
            loc_type = _LOC_TYPE_CANONICAL[token]
            remainder = head_part[len(token):].lstrip(". ").strip()
            location = remainder or None
            break
    if loc_type is None:
        # No recognisable INT/EXT prefix â€” treat the whole head as location.
        location = head_part or None

    time_of_day = _TIME_TOKENS.get(tail_part)
    return (loc_type, location, time_of_day)


_LOC_TYPE_TOKENS = ("INT/EXT", "EXT/INT", "I/E", "INT", "EXT")
_LOC_TYPE_CANONICAL = {
    "INT": "INT",
    "EXT": "EXT",
    "INT/EXT": "INT/EXT",
    "EXT/INT": "INT/EXT",
    "I/E": "INT/EXT",
}
_TIME_TOKENS = {
    "DAY": "DAY",
    "NIGHT": "NIGHT",
    "DAWN": "DAWN",
    "DUSK": "DUSK",
    "MORNING": "MORNING",
    "EVENING": "EVENING",
    "CONTINUOUS": "CONTINUOUS",
}



