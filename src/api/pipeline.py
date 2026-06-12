"""
Pipeline Orchestrator
Accepts a screenplay script, runs schedule + incentive analysis,
and returns a unified production intelligence report.
"""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/pipeline", tags=["Pipeline"])


class OrchestrateRequest(BaseModel):
    script: str
    production_title: Optional[str] = "Untitled Production"
    emotion_override: Optional[str] = None
    genre_override: Optional[str] = None
    jurisdiction_codes: Optional[List[str]] = []
    qualifying_spend_override: Optional[float] = None


class OrchestrateResponse(BaseModel):
    success: bool
    production_title: str
    timestamp: str
    script_stats: dict
    incentive_summary: dict
    recommendations: List[str]
    raw: dict


@router.get("/health")
async def pipeline_health():
    return {
        "status": "operational",
        "service": "SceneIQ Pipeline Orchestrator",
        "timestamp": datetime.utcnow().isoformat()
    }


@router.post("/orchestrate")
async def orchestrate(req: OrchestrateRequest):
    """
    Full pipeline orchestration:
    1. Parse script stats
    2. Estimate budget from page count
    3. Analyze incentives for requested jurisdictions
    4. Return unified report
    """
    try:
        # â”€â”€ Script parsing â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        script_text = req.script or ""
        words       = len(script_text.split())
        lines       = len(script_text.splitlines())
        # Rough page estimate: ~55 lines per page screenplay format
        est_pages   = max(1, round(lines / 55, 1))
        # Rough budget estimate: ~$1M per page for indie, ~$3M for studio
        est_budget  = est_pages * 1_500_000

        if req.qualifying_spend_override:
            qualifying_spend = req.qualifying_spend_override
        else:
            qualifying_spend = est_budget * 0.65  # 65% typical qualifying ratio

        script_stats = {
            "word_count":     words,
            "line_count":     lines,
            "estimated_pages": est_pages,
            "estimated_budget": est_budget,
            "qualifying_spend": qualifying_spend,
        }

        # â”€â”€ Incentive analysis â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        incentive_summary = {
            "jurisdictions_analyzed": len(req.jurisdiction_codes) if req.jurisdiction_codes else 0,
            "estimated_qualifying_spend": qualifying_spend,
            "note": "For detailed incentive analysis, use the Incentives Calculator with specific jurisdiction codes."
        }

        # If jurisdiction codes provided, attempt basic analysis
        jurisdiction_results = []
        if req.jurisdiction_codes:
            from src.utils.database import prisma
            for code in req.jurisdiction_codes[:5]:  # cap at 5
                try:
                    jur = await prisma.jurisdiction.find_first(
                        where={"code": code.upper(), "active": True}
                    )
                    if jur:
                        rules = await prisma.incentiverule.find_many(
                            where={"jurisdictionId": jur.id, "active": True}
                        )
                        for rule in rules:
                            if rule.percentage:
                                credit = qualifying_spend * (float(rule.percentage) / 100)
                                max_c  = float(rule.maxCredit) if rule.maxCredit else None
                                if max_c:
                                    credit = min(credit, max_c)
                                jurisdiction_results.append({
                                    "jurisdiction": jur.name,
                                    "code":         jur.code,
                                    "rule":         rule.ruleName,
                                    "rate":         float(rule.percentage),
                                    "estimated_credit": round(credit, 2),
                                })
                except Exception as e:
                    logger.warning("Jurisdiction lookup failed for %s: %s", code, e)

            if jurisdiction_results:
                jurisdiction_results.sort(key=lambda x: x["estimated_credit"], reverse=True)
                best = jurisdiction_results[0]
                incentive_summary["best_jurisdiction"]   = best["jurisdiction"]
                incentive_summary["best_rate"]           = best["rate"]
                incentive_summary["best_credit"]         = best["estimated_credit"]
                incentive_summary["jurisdiction_results"] = jurisdiction_results

        # â”€â”€ Recommendations â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        recommendations = []
        if est_pages < 80:
            recommendations.append("Script is under 80 pages â€” consider expanding for feature-length qualification in most jurisdictions.")
        if est_pages > 120:
            recommendations.append("Script exceeds 120 pages â€” review pacing for commercial viability.")
        if jurisdiction_results:
            recommendations.append(f"Best incentive option: {jurisdiction_results[0]['jurisdiction']} at {jurisdiction_results[0]['rate']}% â€” estimated credit ${jurisdiction_results[0]['estimated_credit']:,.0f}.")
        if qualifying_spend < 500_000:
            recommendations.append("Qualifying spend below $500K â€” many state programs have minimum spend requirements. Review eligibility carefully.")
        recommendations.append("Run the Compliance Checker after jurisdiction selection to verify all requirements.")
        recommendations.append("Use the Incentive Calculator for precise credit modeling with actual expense line items.")

        return {
            "success":          True,
            "production_title": req.production_title,
            "timestamp":        datetime.utcnow().isoformat(),
            "script_stats":     script_stats,
            "incentive_summary": incentive_summary,
            "recommendations":  recommendations,
            "raw": {
                "script_length":  len(script_text),
                "genre_override": req.genre_override,
                "emotion_override": req.emotion_override,
            }
        }

    except Exception as e:
        logger.error("Pipeline orchestration failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Pipeline failed: {str(e)}")


@router.post("/report")
async def generate_pipeline_report(result: dict):
    """Generate a PDF report from an orchestrate result."""
    try:
        from src.utils.pdf_generator import pdf_generator
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        from reportlab.lib.pagesizes import letter
        from reportlab.lib import colors
        from reportlab.lib.units import inch
        import io

        title  = result.get("production_title", "Untitled")
        stats  = result.get("script_stats", {})
        inc    = result.get("incentive_summary", {})
        recs   = result.get("recommendations", [])

        buffer = io.BytesIO()
        doc    = SimpleDocTemplate(buffer, pagesize=letter,
                                   rightMargin=72, leftMargin=72,
                                   topMargin=72, bottomMargin=18)
        story  = []

        story.append(Paragraph("SceneIQ Pipeline Report", pdf_generator.styles['CustomTitle']))
        story.append(Paragraph(title, pdf_generator.styles['CustomSubtitle']))
        story.append(Paragraph(f"Generated {datetime.now().strftime('%B %d, %Y')}", pdf_generator.styles['CustomSubtitle']))
        story.append(Spacer(1, 0.5 * inch))

        story.append(Paragraph("Script Analysis", pdf_generator.styles['SectionHeader']))
        stats_data = [
            ["Estimated Pages",    str(stats.get("estimated_pages", "â€”"))],
            ["Word Count",         f"{stats.get('word_count', 0):,}"],
            ["Estimated Budget",   f"${stats.get('estimated_budget', 0):,.0f}"],
            ["Qualifying Spend",   f"${stats.get('qualifying_spend', 0):,.0f}"],
        ]
        st = Table(stats_data, colWidths=[2*inch, 4*inch])
        st.setStyle(TableStyle([
            ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (-1,-1), 10),
            ('BOTTOMPADDING', (0,0), (-1,-1), 7),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#eeeeee')),
        ]))
        story.append(st)
        story.append(Spacer(1, 0.3 * inch))

        if inc.get("jurisdiction_results"):
            story.append(Paragraph("Incentive Analysis", pdf_generator.styles['SectionHeader']))
            jur_data = [["Jurisdiction", "Rate", "Est. Credit"]]
            for j in inc["jurisdiction_results"]:
                jur_data.append([j["jurisdiction"], f"{j['rate']}%", f"${j['estimated_credit']:,.0f}"])
            jt = Table(jur_data, colWidths=[2.5*inch, 1*inch, 2*inch])
            jt.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#2c5aa0')),
                ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
                ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                ('FONTSIZE', (0,0), (-1,-1), 10),
                ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cccccc')),
                ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#f0f4ff')]),
            ]))
            story.append(jt)
            story.append(Spacer(1, 0.3 * inch))

        story.append(Paragraph("Recommendations", pdf_generator.styles['SectionHeader']))
        for rec in recs:
            story.append(Paragraph(f"â€¢ {rec}", pdf_generator.styles['Normal']))
            story.append(Spacer(1, 4))

        doc.build(story)
        buffer.seek(0)

        safe = "".join(c for c in title if c.isalnum() or c in " -_").strip().replace(" ","_")
        filename = f"SceneIQ_Pipeline_{safe}_{datetime.now().strftime('%Y%m%d')}.pdf"

        return Response(
            content=buffer.getvalue(),
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'}
        )

    except Exception as e:
        logger.error("Report generation failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Report generation failed: {str(e)}")


