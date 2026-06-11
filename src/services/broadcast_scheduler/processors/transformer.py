# =============================================================================
# src/services/broadcast_scheduler/processors/transformer.py
# Cleans and normalises a parsed Schedule so every field has a consistent
# shape regardless of which parser (CSV / XML / JSON) produced it.
#
# Pipeline contract:
#   - Every field stays a string (or None) after transform â€” no Python
#     int / date objects yet. Keeping strings means the exporter does NOT
#     need special-case logic for typed values.
#   - Transformation is in-place: the same Schedule object is mutated
#     and also returned, so calls can be chained.
# =============================================================================

import re

from src.services.broadcast_scheduler.utils.timecode import normalise_timecode
from src.services.broadcast_scheduler.utils.date_helper import normalise_date


# Toggles the [TRANSFORM] progress prints. Was in config/settings.py originally.
VERBOSE_LOGGING = True


# Cleans and normalises every field of a Schedule and all its Segments.
# Returns the same Schedule object (also mutated) for convenience.
def transform_schedule(schedule):
    if schedule is None:
        return None

    if schedule.channel_name:
        schedule.channel_name = clean_text(schedule.channel_name)

    if schedule.schedule_date:
        normalised = normalise_date(schedule.schedule_date)
        if normalised:
            schedule.schedule_date = normalised

    for segment in schedule.segments:
        transform_segment(segment)

    if VERBOSE_LOGGING:
        print(f"[TRANSFORM] Normalised {len(schedule.segments)} segments")

    return schedule


# Cleans and normalises every field on a single Segment, in place.
def transform_segment(segment):
    # Free-text fields: just whitespace tidy-up
    for field_name in ("title", "episode_title", "channel", "genre"):
        value = getattr(segment, field_name, None)
        if value:
            setattr(segment, field_name, clean_text(value))

    # Timecode fields: pad to HH:MM:SS:FF when possible
    for field_name in ("tx_time", "duration"):
        value = getattr(segment, field_name, None)
        if value:
            setattr(segment, field_name, normalise_timecode(value))

    # Date fields: re-emit in DATE_FORMAT (YYYY-MM-DD) when parseable
    for field_name in ("rights_start", "rights_end"):
        value = getattr(segment, field_name, None)
        if value:
            normalised = normalise_date(value)
            if normalised:
                setattr(segment, field_name, normalised)

    # Numeric-string fields: keep digits only
    for field_name in ("episode_number", "series_number"):
        value = getattr(segment, field_name, None)
        if value:
            setattr(segment, field_name, strip_to_digits(value))

    # asset_id is opaque â€” we don't know its format, so leave it alone


# Strips leading/trailing whitespace and collapses runs of internal
# whitespace into a single space. Returns the value unchanged if it
# isn't a string.
def clean_text(value):
    if not isinstance(value, str):
        return value
    return re.sub(r"\s+", " ", value).strip()


# Strips everything except digits â€” useful when a CSV cell arrives as
# "Ep 142" or "Series 12". If the result is empty, returns the original
# so the validator can flag values that don't contain a number at all.
def strip_to_digits(value):
    if not isinstance(value, str):
        return value
    digits_only = re.sub(r"[^\d]", "", value)
    return digits_only if digits_only else value

