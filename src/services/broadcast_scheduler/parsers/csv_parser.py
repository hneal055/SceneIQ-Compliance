import csv
from pathlib import Path
from src.services.broadcast_scheduler.config.field_maps import CSV_FIELD_MAP
from src.services.broadcast_scheduler.models.schedule import Schedule
from src.services.broadcast_scheduler.models.segment import Segment

CSV_MAX_ROWS = None
VERBOSE_LOGGING = True


def parse_csv_file(file_path, channel_name=None, schedule_date=None):
    file_path = Path(file_path)

    if VERBOSE_LOGGING:
        print(f"[CSV] Reading file: {file_path.name}")

    schedule = Schedule(
        channel_name=channel_name,
        schedule_date=schedule_date,
        source_filename=file_path.name,
    )

    try:
        with open(file_path, mode="r", encoding="utf-8-sig", newline="") as csv_file:
            reader = csv.DictReader(csv_file)
            row_count = 0
            for row in reader:
                if CSV_MAX_ROWS is not None and row_count >= CSV_MAX_ROWS:
                    break

                segment = build_segment_from_row(row)
                schedule.add_segment(segment)
                row_count += 1
    except Exception as error:
        print(f"[CSV] ERROR: could not read CSV: {error}")
        return None

    if schedule.channel_name is None and schedule.segments:
        schedule.channel_name = schedule.segments[0].channel

    return schedule


def build_segment_from_row(row):
    segment = Segment()

    # DEBUG: Print every key found in the CSV row
    print(f"DEBUG: Found headers in CSV: {list(row.keys())}")

    normalized_map = {k.lower().strip(): v for k, v in CSV_FIELD_MAP.items()}

    for csv_column, raw_value in row.items():
        if csv_column is None:
            continue

        clean_column = csv_column.lower().strip()
        internal_field = normalized_map.get(clean_column)

        if internal_field:
            value = raw_value.strip() if raw_value and raw_value.strip() != "" else None
            setattr(segment, internal_field, value)

            # Print specifically when we find a value for daypart
            if internal_field == "daypart":
                print(
                    f"DEBUG: SUCCESS - Mapped daypart: '{value}' from header: '{csv_column}'"
                )

    return segment



