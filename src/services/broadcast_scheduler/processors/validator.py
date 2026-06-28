# =============================================================================
# src/services/broadcast_scheduler/processors/validator.py
# Checks a (preferably already-transformed) Schedule for missing required
# fields and badly-shaped timecodes / dates.
#
# Each problem is returned as an "issue dict":
#   {
#     "level": "error"  | "warning",
#     "segment_index": int | None,   # None = schedule-level issue
#     "field": str | None,
#     "message": str,
#   }
#
# Errors mean the data is unfit for export. Warnings mean it's exportable
# but the user should know. STOP_ON_VALIDATION_ERROR toggles whether we
# bail out at the first error or collect them all.
# =============================================================================

from src.services.broadcast_scheduler.utils.timecode import is_valid_timecode
from src.services.broadcast_scheduler.utils.date_helper import is_valid_date


# Module-level defaults (formerly in config/settings.py).
STOP_ON_VALIDATION_ERROR = False
VERBOSE_LOGGING = True


# Validates a whole Schedule and returns a list of issue dicts.
# An empty list means the Schedule is clean.
def validate_schedule(schedule):
    issues = []

    if schedule is None:
        issues.append(_make_issue("error", None, None,
                                  "Schedule is None â€” parsing likely failed"))
        return issues

    if not schedule.channel_name:
        issues.append(_make_issue("warning", None, "channel_name",
                                  "Schedule has no channel_name"))

    if not schedule.schedule_date:
        issues.append(_make_issue("warning", None, "schedule_date",
                                  "Schedule has no schedule_date"))

    if not schedule.segments:
        issues.append(_make_issue("error", None, None,
                                  "Schedule has no segments"))

    for index, segment in enumerate(schedule.segments):
        segment_issues = validate_segment(segment, index)
        issues.extend(segment_issues)

        # If the user has asked us to stop on the first error, bail now.
        if STOP_ON_VALIDATION_ERROR:
            has_error = any(item["level"] == "error" for item in segment_issues)
            if has_error:
                if VERBOSE_LOGGING:
                    print(f"[VALIDATE] STOP_ON_VALIDATION_ERROR set â€” halted at segment {index}")
                break

    if VERBOSE_LOGGING:
        error_count = sum(1 for item in issues if item["level"] == "error")
        warning_count = sum(1 for item in issues if item["level"] == "warning")
        print(f"[VALIDATE] {error_count} errors, {warning_count} warnings")

    return issues


# Validates a single Segment and returns a list of issue dicts for it.
def validate_segment(segment, index):
    issues = []

    # Required: title
    if not segment.title:
        issues.append(_make_issue("error", index, "title", "missing title"))

    # Required: tx_time (and must look like a timecode)
    if not segment.tx_time:
        issues.append(_make_issue("error", index, "tx_time", "missing tx_time"))
    elif not is_valid_timecode(segment.tx_time):
        issues.append(_make_issue("error", index, "tx_time",
                                  f"invalid timecode format: {segment.tx_time!r}"))

    # Required: duration (and must look like a timecode)
    if not segment.duration:
        issues.append(_make_issue("error", index, "duration", "missing duration"))
    elif not is_valid_timecode(segment.duration):
        issues.append(_make_issue("error", index, "duration",
                                  f"invalid duration format: {segment.duration!r}"))

    # Optional: rights dates â€” warn (not error) if present but unparseable
    if segment.rights_start and not is_valid_date(segment.rights_start):
        issues.append(_make_issue("warning", index, "rights_start",
                                  f"invalid date format: {segment.rights_start!r}"))
    if segment.rights_end and not is_valid_date(segment.rights_end):
        issues.append(_make_issue("warning", index, "rights_end",
                                  f"invalid date format: {segment.rights_end!r}"))

    # Optional: episode / series numbers â€” warn if present but not digits-only
    for field_name in ("episode_number", "series_number"):
        value = getattr(segment, field_name, None)
        if value and not value.isdigit():
            issues.append(_make_issue("warning", index, field_name,
                                      f"expected digits only, got: {value!r}"))

    return issues


# Small builder for the issue-dict shape used throughout this module.
def _make_issue(level, segment_index, field, message):
    return {
        "level": level,
        "segment_index": segment_index,
        "field": field,
        "message": message,
    }




