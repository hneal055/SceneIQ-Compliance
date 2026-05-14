# =============================================================================
# src/services/production_schedule/generators/dood.py
# Day Out of Days (DOOD) grid generator + CSV / PDF exporters.
#
# The DOOD is the industry-standard cast-availability matrix: rows are
# cast members, columns are shoot days, cells carry one of these codes:
#   S    Start    — first day the cast member appears
#   W    Work     — appears in a scene this day
#   H    Hold     — between first and last day, not working
#   T    Travel   — manual-override placeholder (never auto-emitted)
#   F    Finish   — last day the cast member appears
#   SW   Start + Work
#   WF   Work + Finish
#   SWF  Start + Work + Finish (single-day appearance)
#
# All three functions stay in-memory; the Phase 10 router will load
# scenes/cast_members/shoot_days from Prisma by production_id and pass
# them down.
# =============================================================================

import csv
import os
from datetime import datetime
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


# Default output directory for DOOD exports — created on first write.
_DEFAULT_OUTPUT_DIR = Path("data") / "output" / "reports"


# Cell-background palette for the PDF, keyed by code. Codes containing
# "W" share the light-green Work shade; "H" is the light-yellow Hold
# shade; pure "S" / "F" (which the auto-generator doesn't emit on their
# own — they only appear combined with W) get a light-blue shade so a
# manual override stays visually distinct.
_PDF_CELL_COLORS = {
    "W":   colors.HexColor("#c8e6c9"),
    "SW":  colors.HexColor("#c8e6c9"),
    "WF":  colors.HexColor("#c8e6c9"),
    "SWF": colors.HexColor("#c8e6c9"),
    "H":   colors.HexColor("#fff9c4"),
    "S":   colors.HexColor("#bbdefb"),
    "F":   colors.HexColor("#bbdefb"),
    # "T" (manual Travel override) shares Hold-yellow visually so the
    # caller's hand-edits sit alongside auto-emitted Hold days.
    "T":   colors.HexColor("#fff9c4"),
}


# Builds the DOOD grid as a nested dict:
#   {cast_member_id: {day_number: code, ...}}
#
# Cells outside a cast member's first-to-last window are OMITTED from
# the inner dict (the CSV/PDF exporters render those slots as blank).
# Cast members who don't appear in any scene are omitted from the outer
# dict entirely.
#
# Arguments:
#   production_id   — kept on the signature to match the brief's spec /
#                     Phase 10 router contract; unused inside the
#                     function (everything is derived from the lists).
#   cast_members    — list of CastMember dataclass objects
#   shoot_days      — list of ShootDay dataclass objects
#   scenes          — list of Scene dataclass objects (extends brief)
def generate_dood(production_id, cast_members, shoot_days, scenes):
    sorted_days = _sort_days(shoot_days)

    grid = {}

    for cm in cast_members:
        working_day_numbers = _working_day_numbers(cm, scenes, sorted_days)
        if not working_day_numbers:
            continue  # non-working cast member — omit from the DOOD

        first_day = min(working_day_numbers)
        last_day = max(working_day_numbers)

        cm_row = {}
        for day in sorted_days:
            n = day.day_number
            if n < first_day or n > last_day:
                continue  # outside the cast member's window — blank cell

            is_start = n == first_day
            is_finish = n == last_day
            is_working = n in working_day_numbers

            if is_start and is_finish and is_working:
                code = "SWF"
            elif is_start and is_working:
                code = "SW"
            elif is_finish and is_working:
                code = "WF"
            elif is_working:
                code = "W"
            else:
                code = "H"

            cm_row[n] = code

        grid[cm.id] = cm_row

    return grid


# Writes the DOOD grid as a CSV. Header row:
#   Cast Member, Day 1 (2026-01-15), Day 2 (2026-01-16), ...
# Body row per cast member, blank cells where the dict has no entry.
#
# Returns the resolved file path as a string.
def export_dood_csv(
    dood_grid,
    cast_members,
    shoot_days,
    output_dir=None,
    production_id=None,
):
    sorted_days = _sort_days(shoot_days)
    out_dir = _resolve_output_dir(output_dir)
    production_id = production_id or "untitled"
    file_path = out_dir / f"dood_{production_id}.csv"

    # utf-8-sig writes a BOM so Excel opens the file with the right
    # encoding even on Windows (matches the broadcast scheduler's
    # convention — same gotcha, same fix).
    with open(file_path, mode="w", encoding="utf-8-sig", newline="") as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(_csv_header_row(sorted_days))
        for cm in _cast_members_in_grid(cast_members, dood_grid):
            writer.writerow(_csv_body_row(cm, sorted_days, dood_grid))

    return str(file_path)


# Writes the DOOD grid as a colour-coded PDF using reportlab.
#
# Returns the resolved file path as a string.
def export_dood_pdf(
    dood_grid,
    cast_members,
    shoot_days,
    output_dir=None,
    production_id=None,
    production_title=None,
):
    sorted_days = _sort_days(shoot_days)
    out_dir = _resolve_output_dir(output_dir)
    production_id = production_id or "untitled"
    file_path = out_dir / f"dood_{production_id}.pdf"

    # Landscape letter — DOODs are wide tables and portrait crops days.
    doc = SimpleDocTemplate(
        str(file_path),
        pagesize=landscape(letter),
        rightMargin=0.5 * inch,
        leftMargin=0.5 * inch,
        topMargin=0.5 * inch,
        bottomMargin=0.5 * inch,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        name="DoodTitle",
        parent=styles["Heading1"],
        fontSize=16,
        alignment=TA_CENTER,
        spaceAfter=6,
    )
    subtitle_style = ParagraphStyle(
        name="DoodSubtitle",
        parent=styles["Normal"],
        fontSize=10,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#666666"),
        spaceAfter=18,
    )

    title_text = production_title or production_id or "Production"
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

    story = [
        Paragraph(f"{title_text} — Day Out of Days", title_style),
        Paragraph(f"Generated {timestamp}", subtitle_style),
        Spacer(1, 0.1 * inch),
        _build_dood_table(dood_grid, cast_members, sorted_days),
    ]

    doc.build(story, onFirstPage=_pdf_footer, onLaterPages=_pdf_footer)
    return str(file_path)


# -----------------------------------------------------------------------------
# Private helpers
# -----------------------------------------------------------------------------


# Returns the shoot_days list sorted by day_number, leaving the input
# list untouched.
def _sort_days(shoot_days):
    return sorted(shoot_days, key=lambda d: d.day_number)


# Returns the set of day_numbers the cast member works. A cast member
# "works" a day if any scene with that day's id has the cast member's
# id in its cast_ids list. Scene.cast_ids is the FK array of
# CastMember.id values (matches the schema's `castIds` field name).
def _working_day_numbers(cast_member, scenes, sorted_days):
    day_id_to_number = {d.id: d.day_number for d in sorted_days}
    working = set()
    for scene in scenes:
        if scene.shoot_day_id is None:
            continue
        if cast_member.id not in scene.cast_ids:
            continue
        day_number = day_id_to_number.get(scene.shoot_day_id)
        if day_number is not None:
            working.add(day_number)
    return working


# Returns the path to the output directory, defaulting to
# data/output/reports/ and creating it if it doesn't exist.
def _resolve_output_dir(output_dir):
    out = Path(output_dir) if output_dir is not None else _DEFAULT_OUTPUT_DIR
    os.makedirs(out, exist_ok=True)
    return out


# Cast members that actually appear in the grid, in the input order.
def _cast_members_in_grid(cast_members, dood_grid):
    return [cm for cm in cast_members if cm.id in dood_grid]


# Header row: ["Cast Member", "Day 1 (2026-01-15)", ...]. Date is
# appended in parens only when the ShootDay has one.
def _csv_header_row(sorted_days):
    row = ["Cast Member"]
    for day in sorted_days:
        if day.date:
            row.append(f"Day {day.day_number} ({day.date})")
        else:
            row.append(f"Day {day.day_number}")
    return row


# Body row: [character_name, code_for_day_1, code_for_day_2, ...].
def _csv_body_row(cast_member, sorted_days, dood_grid):
    row = [cast_member.character_name]
    cm_codes = dood_grid.get(cast_member.id, {})
    for day in sorted_days:
        row.append(cm_codes.get(day.day_number, ""))
    return row


# Builds the reportlab Table for the PDF — header row + one row per
# working cast member, with cell-background overrides driven by code.
def _build_dood_table(dood_grid, cast_members, sorted_days):
    data = [_csv_header_row(sorted_days)]
    members = _cast_members_in_grid(cast_members, dood_grid)
    for cm in members:
        data.append(_csv_body_row(cm, sorted_days, dood_grid))

    table = Table(data, repeatRows=1)

    style_cmds = [
        # Header row
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2c5aa0")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 10),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),

        # Body
        ("FONTSIZE", (0, 1), (-1, -1), 9),
        ("ALIGN", (1, 1), (-1, -1), "CENTER"),  # codes centred
        ("ALIGN", (0, 1), (0, -1), "LEFT"),     # names left-aligned
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#bdbdbd")),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]

    # Per-cell BACKGROUND overrides for the colour-coded body cells.
    # Row indices in data: 0 = header, 1..N = members. Column indices:
    # 0 = name, 1..D = day codes.
    for row_index, cm in enumerate(members, start=1):
        cm_codes = dood_grid.get(cm.id, {})
        for col_index, day in enumerate(sorted_days, start=1):
            code = cm_codes.get(day.day_number)
            if not code:
                continue
            shade = _PDF_CELL_COLORS.get(code)
            if shade is None:
                continue
            style_cmds.append(
                ("BACKGROUND", (col_index, row_index), (col_index, row_index), shade)
            )

    table.setStyle(TableStyle(style_cmds))
    return table


# Page-number footer drawn by reportlab on every page.
def _pdf_footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#888888"))
    page_size = canvas._pagesize
    canvas.drawCentredString(page_size[0] / 2.0, 0.25 * inch, f"Page {doc.page}")
    canvas.restoreState()
