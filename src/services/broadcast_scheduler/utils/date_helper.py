# =============================================================================
# src/services/broadcast_scheduler/utils/date_helper.py
# Reusable helpers for date strings used across the parser.
#
# normalise_date() is loose: it accepts a wide range of inputs via
# python-dateutil. is_valid_date() is strict: it only passes values that
# already match DATE_FORMAT exactly (so the transformer runs first).
# =============================================================================

from datetime import datetime

from dateutil import parser as dateutil_parser


# Output date format (formerly in config/settings.py).
DATE_FORMAT = "%Y-%m-%d"


# Returns True if value is a string that strict-parses as DATE_FORMAT
# (i.e. YYYY-MM-DD).
def is_valid_date(value):
    if not isinstance(value, str):
        return False
    try:
        datetime.strptime(value, DATE_FORMAT)
        return True
    except ValueError:
        return False


# Returns the value re-emitted in DATE_FORMAT (e.g. YYYY-MM-DD), or None
# if the value can't be parsed as a date at all. dateutil handles many
# common shapes: "2026-1-1", "1/1/2026", "Jan 1 2026", etc.
def normalise_date(value):
    if not isinstance(value, str):
        return None
    value = value.strip()
    if not value:
        return None
    try:
        parsed = dateutil_parser.parse(value, dayfirst=False)
        return parsed.strftime(DATE_FORMAT)
    except (ValueError, TypeError, OverflowError):
        return None



