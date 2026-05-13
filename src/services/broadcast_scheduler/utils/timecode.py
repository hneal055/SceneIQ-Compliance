# =============================================================================
# src/services/broadcast_scheduler/utils/timecode.py
# Reusable helpers for broadcast timecodes in HH:MM:SS:FF form.
#
# Two callers use these today:
#   - processors/transformer.py uses normalise_timecode() to pad raw input
#   - processors/validator.py uses is_valid_timecode() to strict-check it
# =============================================================================

import re


# Strict HH:MM:SS:FF — exactly two digits per part. Compiled once at module
# load so callers don't pay re-compile cost per call.
_TIMECODE_PATTERN = re.compile(r"^\d{2}:\d{2}:\d{2}:\d{2}$")


# Returns True if value is a string matching HH:MM:SS:FF exactly.
def is_valid_timecode(value):
    if not isinstance(value, str):
        return False
    return _TIMECODE_PATTERN.match(value) is not None


# Returns the value re-emitted as HH:MM:SS:FF (zero-padded), or the
# original value if it can't be split into four numeric parts. Examples:
#   "6:00:00:0"   -> "06:00:00:00"
#   "06:00:00:00" -> "06:00:00:00"
#   "garbage"     -> "garbage"   (validator will flag it)
def normalise_timecode(value):
    if not isinstance(value, str):
        return value
    parts = value.strip().split(":")
    if len(parts) != 4:
        return value
    try:
        return ":".join(f"{int(part):02d}" for part in parts)
    except ValueError:
        return value
