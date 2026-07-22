"""
calculator_export.py — PDF export for Scenario Calculator results
POST /calculator/scenario/export — returns a PDF report

Runs the same scenario calculation and formats the results as a
downloadable PDF with jurisdiction, scenario comparison table,
best/worst analysis, and recommendations.
"""
import logging
import os
import json
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import FileResponse
from pydantic import BaseModel

from src.utils.database import prisma
from src.models.calculator import ScenarioCalculateRequest

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Calculator Export"])


@router.post(
    "/calculator/scenario/export",
    summary="Export scenario calculation results as a PDF report",
)
async def export_scenario_pdf(request: ScenarioCalculateRequest):
    """
    Runs the scenario calculation and returns a formatted PDF report
    suitable for sharing with producers, financiers, or bond companies.
    """
    # Import and run the calculation
    from src.api.calculator import calculate_scenarios
    result = await calculate_scenarios(request)

    # Build HTML for PDF conversion
    scenarios_html = ""
    for s in result.scenarios:
        met = "Yes" if s.meetsRequirements else "No"
        scenarios_html += f"""
        <tr>
            <td>{s.scenarioName}</td>
            <td>{s.bestRuleName}</td>
            <td>${s.estimatedCredit:,.0f}</td>
            <td>{s.effectiveRate:.1f}%</td>
            <td>{met}</td>
        </tr>"""

    recs_html = ""
    for r in result.recommendations:
        recs_html += f"<li>{r}</li>"

    prod_date = result.productionDate.isoformat() if result.productionDate else "Not specified"

    html = f"""<!DOCTYPE html>
<html>
<head>
<style>
    body {{ font-family: Calibri, Arial, sans-serif; margin: 40px; color: #1A1A2E; font-size: 14px; }}
    h1 {{ color: #1A1A2E; font-size: 24px; border-bottom: 3px solid #C9973A; padding-bottom: 8px; }}
    h2 {{ color: #C9973A; font-size: 18px; margin-top: 24px; }}
    .header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }}
    .logo {{ font-size: 28px; font-weight: bold; color: #1A1A2E; }}
    .subtitle {{ color: #C9973A; font-size: 16px; }}
    .meta {{ color: #555; font-size: 12px; margin-bottom: 20px; }}
    table {{ width: 100%; border-collapse: collapse; margin: 16px 0; }}
    th {{ background: #1A1A2E; color: white; padding: 10px 12px; text-align: left; font-size: 13px; }}
    td {{ padding: 8px 12px; border-bottom: 1px solid #ddd; font-size: 13px; }}
    tr:nth-child(even) {{ background: #f8f6f2; }}
    .summary {{ background: #f4f0e8; padding: 16px; border-radius: 8px; margin: 16px 0; }}
    .summary-grid {{ display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 16px; }}
    .summary-item {{ text-align: center; }}
    .summary-label {{ font-size: 11px; color: #555; text-transform: uppercase; }}
    .summary-value {{ font-size: 20px; font-weight: bold; color: #1A1A2E; }}
    .best {{ color: #28a745; }}
    .recs {{ background: #fff8e1; padding: 12px 16px; border-left: 4px solid #C9973A; margin: 16px 0; }}
    .recs li {{ margin: 4px 0; }}
    .footer {{ margin-top: 40px; padding-top: 12px; border-top: 1px solid #ddd; color: #999; font-size: 11px; text-align: center; }}
</style>
</head>
<body>
    <div class="header">
        <div>
            <div class="logo">SceneIQ</div>
            <div class="subtitle">Scenario Calculator Report</div>
        </div>
        <div class="meta">Generated: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}</div>
    </div>

    <h1>Incentive Scenario Analysis</h1>

    <div class="summary">
        <div class="summary-grid">
            <div class="summary-item">
                <div class="summary-label">Jurisdiction</div>
                <div class="summary-value">{result.jurisdiction}</div>
            </div>
            <div class="summary-item">
                <div class="summary-label">Production Budget</div>
                <div class="summary-value">${result.baseProductionBudget:,.0f}</div>
            </div>
            <div class="summary-item">
                <div class="summary-label">Production Date</div>
                <div class="summary-value">{prod_date}</div>
            </div>
        </div>
    </div>

    <h2>Scenario Comparison</h2>
    <table>
        <thead>
            <tr>
                <th>Scenario</th>
                <th>Best Rule</th>
                <th>Estimated Credit</th>
                <th>Effective Rate</th>
                <th>Requirements Met</th>
            </tr>
        </thead>
        <tbody>
            {scenarios_html}
        </tbody>
    </table>

    <h2>Best vs Worst Analysis</h2>
    <div class="summary">
        <div class="summary-grid">
            <div class="summary-item">
                <div class="summary-label">Best Scenario</div>
                <div class="summary-value best">{result.bestScenario.scenarioName}</div>
                <div>${result.bestScenario.estimatedCredit:,.0f} ({result.bestScenario.effectiveRate:.1f}%)</div>
            </div>
            <div class="summary-item">
                <div class="summary-label">Worst Scenario</div>
                <div class="summary-value">{result.worstScenario.scenarioName}</div>
                <div>${result.worstScenario.estimatedCredit:,.0f} ({result.worstScenario.effectiveRate:.1f}%)</div>
            </div>
            <div class="summary-item">
                <div class="summary-label">Savings Difference</div>
                <div class="summary-value best">${result.savingsDifference:,.0f}</div>
            </div>
        </div>
    </div>

    <h2>Recommendations</h2>
    <div class="recs">
        <ul>{recs_html if recs_html else '<li>No specific recommendations for these scenarios.</li>'}</ul>
    </div>

    <div class="summary">
        <p><strong>Available Rules:</strong> {result.availableRules} | <strong>Expired Rules:</strong> {result.expiredRules}</p>
    </div>

    <div class="footer">
        SceneIQ Autonomous Production OS - Scene Reader Studio Technologies LLC - Chicago, Illinois<br>
        This report is generated from live platform data and is intended for production planning purposes only.
    </div>
</body>
</html>"""

    # Write HTML and convert to PDF
    report_dir = "/tmp/reports"
    os.makedirs(report_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    html_path = f"{report_dir}/scenario_{timestamp}.html"
    pdf_path = f"{report_dir}/scenario_{timestamp}.pdf"

    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)

    # Try weasyprint for PDF conversion, fall back to HTML download
    try:
        from weasyprint import HTML
        HTML(filename=html_path).write_pdf(pdf_path)
        return FileResponse(
            pdf_path,
            media_type="application/pdf",
            filename=f"SceneIQ_Scenario_Report_{timestamp}.pdf",
        )
    except ImportError:
        # weasyprint not installed - return HTML directly
        return FileResponse(
            html_path,
            media_type="text/html",
            filename=f"SceneIQ_Scenario_Report_{timestamp}.html",
        )
