# =============================================================================
# src/services/production_schedule/generators/call_sheet.py
# Call sheet builder + PDF / JSON exporters.
#
# A call sheet is the daily plan handed to cast and crew for one shoot
# day. It carries the general crew call time, the shooting location,
# nearest hospital, the scene list for the day, and department-by-
# department crew call times.
#
# Following the Phase 5/6 pattern:
#   - generate_call_sheet builds a CallSheet dataclass purely in-memory.
#   - The Phase 10 router will persist the returned object via Prisma.
#
# Public functions:
#   generate_call_sheet(shoot_day, scenes, crew_calls, production)
#       Returns a populated CallSheet object — no DB writes.
#   export_call_sheet_pdf(call_sheet, *, production_title=None, episode=None,
#                         output_dir=None)
#       Writes a portrait-letter PDF and returns the file path.
#   export_call_sheet_json(call_sheet)
#       Returns a JSON-serialisable dict; None fields pass through
#       so json.dumps renders them as null.
# =============================================================================

import os
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from src.services.production_schedule.models.call_sheet import CallSheet


# Default output directory for call-sheet exports — created on first write.
_DEFAULT_OUTPUT_DIR = Path("data") / "output" / "reports"


# Builds a CallSheet from one shoot day plus the scenes scheduled on it.
#
# Arguments:
#   shoot_day   — ShootDay dataclass (must have .id, .day_number).
#                 .date / .call_time / .location / .nearest_hospital
#                 default through to the CallSheet when present.
#   scenes      — list of Scene dataclasses scheduled on this shoot day.
#                 The caller is expected to filter — generate_call_sheet
#                 takes the list as-is and snapshots it.
#   crew_calls  — list of dicts: {"department": str, "name": str,
#                 "call_time": str}. Stored verbatim on
#                 CallSheet.crew_calls so the PDF can render the table
#                 directly from the saved object.
#   production  — object with .id and .title (other fields ignored
#                 here; PDF rendering pulls cosmetic fields separately).
#
# Returns the CallSheet object. Does NOT persist to the DB — the
# Phase 10 router handles `await prisma.callsheet.create(...)`.
def generate_call_sheet(shoot_day, scenes, crew_calls, production):
    scene_snapshots = [_scene_snapshot(s) for s in scenes]
    crew_snapshots = [_crew_snapshot(c) for c in (crew_calls or [])]

    return CallSheet(
        day_number=shoot_day.day_number,
        shoot_day_id=shoot_day.id,
        production_id=getattr(production, "id", None) if production is not None else None,
        date=getattr(shoot_day, "date", None),
        general_call=getattr(shoot_day, "call_time", None),
        location=getattr(shoot_day, "location", None),
        nearest_hospital=getattr(shoot_day, "nearest_hospital", None),
        weather=None,  # placeholder — populated manually or via weather API later
        scenes=scene_snapshots,
        crew_calls=crew_snapshots,
    )


# Returns the CallSheet as a JSON-serialisable dict. dataclasses.asdict()
# recurses into list-of-dicts naturally; None fields stay None so
# json.dumps renders them as null without further work.
def export_call_sheet_json(call_sheet):
    return asdict(call_sheet)


# Generates a portrait-letter PDF call sheet using reportlab. Returns
# the resolved file path as a string.
#
# Sections (in order):
#   1. Header        — production title, episode, day number, date
#   2. General call  — large prominent time
#   3. Location      — name and address
#   4. Hospital      — name and address
#   5. Weather       — placeholder text
#   6. Scene list    — 7-column table
#   7. Crew calls    — 3-column table
def export_call_sheet_pdf(
    call_sheet,
    *,
    production_title=None,
    episode=None,
    output_dir=None,
):
    out_dir = _resolve_output_dir(output_dir)
    file_path = _pdf_path(out_dir, call_sheet)

    doc = SimpleDocTemplate(
        str(file_path),
        pagesize=letter,
        rightMargin=0.6 * inch,
        leftMargin=0.6 * inch,
        topMargin=0.6 * inch,
        bottomMargin=0.6 * inch,
    )

    styles = _build_styles()
    story = []

    story.extend(_header_section(call_sheet, production_title, episode, styles))
    story.extend(_general_call_section(call_sheet, styles))
    story.extend(_location_section(call_sheet, styles))
    story.extend(_hospital_section(call_sheet, styles))
    story.extend(_weather_section(call_sheet, styles))
    story.extend(_scene_list_section(call_sheet, styles))
    story.extend(_crew_calls_section(call_sheet, styles))

    doc.build(story, onFirstPage=_pdf_footer, onLaterPages=_pdf_footer)
    return str(file_path)


# -----------------------------------------------------------------------------
# Private helpers — snapshot shapes
# -----------------------------------------------------------------------------


# Converts a Scene dataclass into the dict-shape stored on
# CallSheet.scenes. The PDF's scene-list table maps these keys directly
# to its 7 columns.
def _scene_snapshot(scene) -> Dict[str, Any]:
    return {
        "scene_number": scene.scene_number,
        "title": scene.title,
        "location": scene.location,
        "location_type": scene.location_type,
        "time_of_day": scene.time_of_day,
        "page_count": scene.page_count,
        "cast": list(scene.cast_ids) if scene.cast_ids else [],
    }


# Normalises caller-supplied crew_call dicts. We accept any dict shape
# with the three keys we care about; unknown extras pass through
# silently so callers can stash department-specific metadata.
def _crew_snapshot(crew_call: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "department": crew_call.get("department"),
        "name": crew_call.get("name"),
        "call_time": crew_call.get("call_time"),
        **{k: v for k, v in crew_call.items() if k not in {"department", "name", "call_time"}},
    }


# -----------------------------------------------------------------------------
# Private helpers — PDF assembly
# -----------------------------------------------------------------------------


def _resolve_output_dir(output_dir):
    out = Path(output_dir) if output_dir is not None else _DEFAULT_OUTPUT_DIR
    os.makedirs(out, exist_ok=True)
    return out


def _pdf_path(out_dir, call_sheet):
    pid = call_sheet.production_id or "untitled"
    return out_dir / f"call_sheet_{pid}_day_{call_sheet.day_number}.pdf"


def _build_styles():
    styles = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            name="CSTitle",
            parent=styles["Heading1"],
            fontSize=20,
            alignment=TA_CENTER,
            spaceAfter=4,
        ),
        "subtitle": ParagraphStyle(
            name="CSSubtitle",
            parent=styles["Normal"],
            fontSize=11,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#666666"),
            spaceAfter=14,
        ),
        "section_header": ParagraphStyle(
            name="CSSectionHeader",
            parent=styles["Heading2"],
            fontSize=12,
            textColor=colors.HexColor("#2c5aa0"),
            spaceBefore=10,
            spaceAfter=4,
            fontName="Helvetica-Bold",
        ),
        "general_call": ParagraphStyle(
            name="CSGeneralCall",
            parent=styles["Heading1"],
            fontSize=28,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#c62828"),
            spaceBefore=2,
            spaceAfter=10,
            fontName="Helvetica-Bold",
        ),
        "body": ParagraphStyle(
            name="CSBody",
            parent=styles["Normal"],
            fontSize=10,
            alignment=TA_LEFT,
            spaceAfter=4,
        ),
    }


def _header_section(call_sheet, production_title, episode, styles) -> List:
    title_text = production_title or call_sheet.production_id or "Production"
    date_text = call_sheet.date or "—"
    bits = [f"Day {call_sheet.day_number}", date_text]
    if episode:
        bits.insert(0, f"Episode {episode}")
    subtitle = "  ·  ".join(bits)
    return [
        Paragraph(title_text, styles["title"]),
        Paragraph(subtitle, styles["subtitle"]),
    ]


def _general_call_section(call_sheet, styles) -> List:
    call_time = call_sheet.general_call or "—"
    return [
        Paragraph("General Call", styles["section_header"]),
        Paragraph(call_time, styles["general_call"]),
    ]


def _location_section(call_sheet, styles) -> List:
    body = call_sheet.location or "(no location set)"
    return [
        Paragraph("Location", styles["section_header"]),
        Paragraph(body, styles["body"]),
    ]


def _hospital_section(call_sheet, styles) -> List:
    body = call_sheet.nearest_hospital or "(no hospital on file)"
    return [
        Paragraph("Nearest Hospital", styles["section_header"]),
        Paragraph(body, styles["body"]),
    ]


def _weather_section(call_sheet, styles) -> List:
    body = call_sheet.weather or "(weather to be confirmed on the day)"
    return [
        Paragraph("Weather", styles["section_header"]),
        Paragraph(body, styles["body"]),
    ]


def _scene_list_section(call_sheet, styles) -> List:
    header_row = [
        "Scene #",
        "Title",
        "Location",
        "Int/Ext",
        "Day/Night",
        "Pages",
        "Cast",
    ]
    body_rows = []
    for snap in call_sheet.scenes or []:
        body_rows.append(
            [
                snap.get("scene_number") or "",
                snap.get("title") or "",
                snap.get("location") or "",
                snap.get("location_type") or "",
                snap.get("time_of_day") or "",
                _format_pages(snap.get("page_count")),
                ", ".join(snap.get("cast") or []),
            ]
        )

    if not body_rows:
        body_rows = [["—", "(no scenes scheduled)", "", "", "", "", ""]]

    table = Table([header_row] + body_rows, repeatRows=1, colWidths=[
        0.6 * inch, 1.9 * inch, 1.4 * inch, 0.55 * inch, 0.65 * inch, 0.45 * inch, 1.7 * inch
    ])
    table.setStyle(_table_style(len(body_rows)))

    return [
        Paragraph("Scenes", styles["section_header"]),
        table,
        Spacer(1, 0.15 * inch),
    ]


def _crew_calls_section(call_sheet, styles) -> List:
    header_row = ["Department", "Name", "Call Time"]
    body_rows = [
        [
            cc.get("department") or "",
            cc.get("name") or "",
            cc.get("call_time") or "",
        ]
        for cc in (call_sheet.crew_calls or [])
    ]

    if not body_rows:
        body_rows = [["—", "(no crew calls set)", ""]]

    table = Table([header_row] + body_rows, repeatRows=1, colWidths=[
        2.0 * inch, 2.8 * inch, 1.4 * inch,
    ])
    table.setStyle(_table_style(len(body_rows)))

    # Keep the crew table on a single block so a page break doesn't
    # split the header off from its rows.
    return [
        KeepTogether([
            Paragraph("Crew Calls", styles["section_header"]),
            table,
        ]),
    ]


# Common table style: dark-blue header row, light-grey grid, centred
# body text by default. `body_row_count` is unused for now but kept on
# the signature for future per-row striping.
def _table_style(body_row_count):
    _ = body_row_count  # reserved
    return TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2c5aa0")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 9),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
        ("FONTSIZE", (0, 1), (-1, -1), 8),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#bdbdbd")),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ])


# Formats a page-count value for the scene-list table. Drops trailing
# zeros for whole pages, blank for None.
def _format_pages(value):
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


# Page-number footer printed on every page.
def _pdf_footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#888888"))
    page_size = canvas._pagesize
    canvas.drawCentredString(page_size[0] / 2.0, 0.3 * inch, f"Page {doc.page}")
    canvas.restoreState()
