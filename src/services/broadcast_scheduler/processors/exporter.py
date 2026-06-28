# =============================================================================
# src/services/broadcast_scheduler/processors/exporter.py
# Writes a Schedule out to disk as CSV, JSON, or XML.
#
# Unlike the standalone parser this came from, no path defaults are baked
# in â€” output_dir is a required argument so SceneIQ can decide where to
# write (e.g. a temp folder per request, or never call this at all because
# the data is being persisted to PostgreSQL instead).
# =============================================================================

import csv
import json
from pathlib import Path
from xml.sax.saxutils import escape


# Module-level defaults (formerly in config/settings.py).
DEFAULT_EXPORT_FORMAT = "csv"
VERBOSE_LOGGING = True


# Order of columns / keys / XML tags in the output. Every parser populates
# the same Segment fields, so this list is also the contract.
EXPORT_FIELDS = [
    "title",
    "episode_title",
    "tx_time",
    "duration",
    "episode_number",
    "series_number",
    "channel",
    "genre",
    "rights_start",
    "rights_end",
    "asset_id",
]


# Top-level entry point â€” writes the given Schedule out to disk.
# Returns the Path of the written file on success, or None on failure.
#
# Arguments:
#   schedule       â€” the Schedule to write
#   output_dir     â€” folder for the output file (REQUIRED â€” caller decides)
#   export_format  â€” "csv", "json", or "xml" (defaults to DEFAULT_EXPORT_FORMAT)
#   filename       â€” output filename (defaults to "{source-stem}_parsed.{ext}")
def export_schedule(schedule, output_dir, export_format=None, filename=None):
    if schedule is None:
        print("[EXPORT] ERROR: Schedule is None â€” nothing to export")
        return None
    if not schedule.segments:
        print("[EXPORT] ERROR: Schedule has no segments â€” nothing to export")
        return None
    if output_dir is None:
        print("[EXPORT] ERROR: output_dir is required (caller must specify)")
        return None

    output_dir = Path(output_dir)
    export_format = (export_format or DEFAULT_EXPORT_FORMAT).lower()

    if filename is None:
        # Include the source file's extension in the output name so that
        # parsing e.g. rundown.csv and rundown.xml produces two distinct
        # output files instead of one silently overwriting the other.
        source_path = Path(schedule.source_filename or "schedule")
        source_stem = source_path.stem
        source_ext = source_path.suffix.lstrip(".")
        if source_ext:
            filename = f"{source_stem}_{source_ext}_parsed.{export_format}"
        else:
            filename = f"{source_stem}_parsed.{export_format}"

    output_path = output_dir / filename

    # Make sure the output folder exists before we try to write into it
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
    except OSError as error:
        print(f"[EXPORT] ERROR: could not create output folder: {error}")
        return None

    if VERBOSE_LOGGING:
        print(f"[EXPORT] Writing {len(schedule.segments)} segments to: {output_path}")

    if export_format == "csv":
        success = export_to_csv(schedule, output_path)
    elif export_format == "json":
        success = export_to_json(schedule, output_path)
    elif export_format == "xml":
        success = export_to_xml(schedule, output_path)
    else:
        print(f"[EXPORT] ERROR: unsupported format: {export_format!r} "
              f"(supported: csv, json, xml)")
        return None

    if not success:
        return None

    if VERBOSE_LOGGING:
        print(f"[EXPORT] Wrote {output_path}")

    return output_path


# Writes the schedule as a CSV file (one header row + one row per segment).
def export_to_csv(schedule, output_path):
    try:
        with open(output_path, mode="w", encoding="utf-8", newline="") as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=EXPORT_FIELDS)
            writer.writeheader()
            for segment in schedule.segments:
                row = {}
                for field_name in EXPORT_FIELDS:
                    value = getattr(segment, field_name, None)
                    row[field_name] = "" if value is None else value
                writer.writerow(row)
        return True
    except OSError as error:
        print(f"[EXPORT] ERROR writing CSV: {error}")
        return False


# Writes the schedule as a JSON file with metadata + segment list.
def export_to_json(schedule, output_path):
    try:
        payload = {
            "channel": schedule.channel_name,
            "date": schedule.schedule_date,
            "source": schedule.source_filename,
            "segments": [
                {field_name: getattr(segment, field_name, None)
                 for field_name in EXPORT_FIELDS}
                for segment in schedule.segments
            ],
        }
        with open(output_path, mode="w", encoding="utf-8") as json_file:
            json.dump(payload, json_file, indent=2, ensure_ascii=False)
        return True
    except OSError as error:
        print(f"[EXPORT] ERROR writing JSON: {error}")
        return False


# Writes the schedule as a flat XML document with one ScheduleEvent per
# segment. All text content is escaped to keep the XML well-formed.
def export_to_xml(schedule, output_path):
    try:
        lines = ['<?xml version="1.0" encoding="UTF-8"?>']
        channel_attr = escape(schedule.channel_name or "")
        date_attr = escape(schedule.schedule_date or "")
        lines.append(f'<BroadcastSchedule channel="{channel_attr}" date="{date_attr}">')

        for segment in schedule.segments:
            lines.append("  <ScheduleEvent>")
            for field_name in EXPORT_FIELDS:
                value = getattr(segment, field_name, None)
                if value is None or value == "":
                    continue  # skip empty fields for tidier XML
                tag = field_to_xml_tag(field_name)
                lines.append(f"    <{tag}>{escape(str(value))}</{tag}>")
            lines.append("  </ScheduleEvent>")

        lines.append("</BroadcastSchedule>")

        with open(output_path, mode="w", encoding="utf-8") as xml_file:
            xml_file.write("\n".join(lines) + "\n")
        return True
    except OSError as error:
        print(f"[EXPORT] ERROR writing XML: {error}")
        return False


# Converts an internal snake_case field name to PascalCase for XML output.
# e.g. tx_time -> TxTime, episode_number -> EpisodeNumber, asset_id -> AssetId.
def field_to_xml_tag(field_name):
    return "".join(part.capitalize() for part in field_name.split("_"))




