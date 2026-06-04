# =============================================================================
# PATCH: Add to parsers/csv_parser.py
# Extracts schedule_date from the filename automatically.
# Supports formats: YYYY-MM-DD, DD-MM-YYYY, DD_MM_YYYY, YYYYMMDD
# Example filenames that work:
#   BBC_ONE_2026-05-13.csv
#   channel4_13-05-2026.csv
#   ITV_20260513.csv
#   sky_sports_2026_05_13.csv
# =============================================================================

import re
from pathlib import Path
from datetime import datetime


def extract_date_from_filename(filepath):
    """
    Looks for a date pattern inside the filename and returns it
    as a YYYY-MM-DD string. Returns None if no date is found.

    Supported patterns in the filename:
      YYYY-MM-DD  e.g. 2026-05-13
      DD-MM-YYYY  e.g. 13-05-2026
      YYYY_MM_DD  e.g. 2026_05_13
      DD_MM_YYYY  e.g. 13_05_2026
      YYYYMMDD    e.g. 20260513
    """

    # Get just the filename without the folder path or extension
    stem = Path(filepath).stem  # e.g. "BBC_ONE_2026-05-13"

    # --- Pattern 1: YYYY-MM-DD or YYYY_MM_DD ---
    match = re.search(r'(20\d{2})[-_](0[1-9]|1[0-2])[-_](0[1-9]|[12]\d|3[01])', stem)
    if match:
        year, month, day = match.group(1), match.group(2), match.group(3)
        return f"{year}-{month}-{day}"

    # --- Pattern 2: DD-MM-YYYY or DD_MM_YYYY ---
    match = re.search(r'(0[1-9]|[12]\d|3[01])[-_](0[1-9]|1[0-2])[-_](20\d{2})', stem)
    if match:
        day, month, year = match.group(1), match.group(2), match.group(3)
        return f"{year}-{month}-{day}"

    # --- Pattern 3: YYYYMMDD (no separator) ---
    match = re.search(r'(20\d{2})(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])', stem)
    if match:
        year, month, day = match.group(1), match.group(2), match.group(3)
        # Basic sanity check — make sure it parses as a real date
        try:
            datetime.strptime(f"{year}{month}{day}", "%Y%m%d")
            return f"{year}-{month}-{day}"
        except ValueError:
            pass  # Not a real date — keep looking

    # No date found in filename
    return None


# =============================================================================
# HOW TO ADD THIS TO parse_csv_file()
# Find the existing parse_csv_file() function in csv_parser.py and update
# the section where schedule_date is set. Replace:
#
#     schedule.schedule_date = extract_date_from_filename(filepath)
if schedule.schedule_date:
    logging.info("Date extracted from filename: %s", schedule.schedule_date)
else:
    logging.warning("No date found in filename: %s", Path(filepath).name)
#
# With:
#
#     schedule.schedule_date = extract_date_from_filename(filepath)
#     if schedule.schedule_date:
#         logging.info("Date extracted from filename: %s", schedule.schedule_date)
#     else:
#         logging.warning("No date found in filename: %s", Path(filepath).name)
#
# =============================================================================


# =============================================================================
# RECOMMENDED FILENAME CONVENTIONS
# Use one of these naming patterns for your CSV schedule files:
#
#   CHANNEL_YYYY-MM-DD.csv        BBC_ONE_2026-05-13.csv      (recommended)
#   CHANNEL_YYYYMMDD.csv          ITV_20260513.csv
#   CHANNEL_DD-MM-YYYY.csv        CHANNEL4_13-05-2026.csv
#
# The channel name can contain letters, numbers, and underscores.
# The date just needs to appear somewhere in the filename.
# =============================================================================


# =============================================================================
# QUICK TEST — run this file directly to verify the function works:
#   python parsers/csv_parser_date_patch.py
# =============================================================================

if __name__ == "__main__":
    test_cases = [
        ("BBC_ONE_2026-05-13.csv",       "2026-05-13"),
        ("channel4_13-05-2026.csv",      "2026-05-13"),
        ("ITV_20260513.csv",             "2026-05-13"),
        ("sky_sports_2026_05_13.csv",    "2026-05-13"),
        ("rundown_13_05_2026.csv",       "2026-05-13"),
        ("no_date_in_here.csv",          None),
        ("sample_rundown.csv",           None),
    ]

    print("Testing extract_date_from_filename()\n")
    all_passed = True
    for filename, expected in test_cases:
        result = extract_date_from_filename(filename)
        status = "PASS" if result == expected else "FAIL"
        if status == "FAIL":
            all_passed = False
        print(f"  [{status}]  {filename:<40} → {str(result):<12}  (expected {expected})")

    print()
    if all_passed:
        print("All tests passed.")
    else:
        print("Some tests failed — check the patterns above.")