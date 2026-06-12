"""
PDF Report Generator
Professional PDF generation for tax incentive reports
"""
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from datetime import datetime
from typing import List, Dict, Any
import io


class PDFReportGenerator:
    """Generate professional PDF reports"""
    
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
    
    def _setup_custom_styles(self):
        """Setup custom paragraph styles"""
        # Title style
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#1a1a1a'),
            spaceAfter=30,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        ))
        
        # Subtitle style
        self.styles.add(ParagraphStyle(
            name='CustomSubtitle',
            parent=self.styles['Heading2'],
            fontSize=14,
            textColor=colors.HexColor('#666666'),
            spaceAfter=20,
            alignment=TA_CENTER
        ))
        
        # Section header
        self.styles.add(ParagraphStyle(
            name='SectionHeader',
            parent=self.styles['Heading2'],
            fontSize=16,
            textColor=colors.HexColor('#2c5aa0'),
            spaceAfter=12,
            spaceBefore=20,
            fontName='Helvetica-Bold'
        ))
        
        # Highlight box
        self.styles.add(ParagraphStyle(
            name='HighlightBox',
            parent=self.styles['Normal'],
            fontSize=12,
            textColor=colors.HexColor('#2c5aa0'),
            fontName='Helvetica-Bold',
            spaceAfter=6
        ))
    
    def generate_comparison_report(
        self,
        production_title: str,
        budget: float,
        comparisons: List[Dict[str, Any]],
        best_option: Dict[str, Any]
    ) -> bytes:
        """Generate jurisdiction comparison report"""
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=18
        )
        
        story = []
        
        # Title
        story.append(Paragraph("Tax Incentive Comparison Report", self.styles['CustomTitle']))
        story.append(Paragraph(
            f"Generated on {datetime.now().strftime('%B %d, %Y')}",
            self.styles['CustomSubtitle']
        ))
        story.append(Spacer(1, 0.5 * inch))
        
        # Production Info
        story.append(Paragraph("Production Information", self.styles['SectionHeader']))
        prod_data = [
            ['Production Title:', production_title],
            ['Total Budget:', f'${budget:,.0f}'],
            ['Analysis Date:', datetime.now().strftime('%B %d, %Y')]
        ]
        prod_table = Table(prod_data, colWidths=[2*inch, 4*inch])
        prod_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#333333')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        story.append(prod_table)
        story.append(Spacer(1, 0.3 * inch))
        
        # Executive Summary
        story.append(Paragraph("Executive Summary", self.styles['SectionHeader']))
        
        # Only show summary if best_option has data
        if best_option and best_option.get('jurisdiction'):
            story.append(Paragraph(
                f"<b>Recommended Location:</b> {best_option['jurisdiction']}",
                self.styles['HighlightBox']
            ))
            story.append(Paragraph(
                f"<b>Estimated Tax Credit:</b> ${best_option.get('estimatedCredit', 0):,.0f}",
                self.styles['HighlightBox']
            ))
            story.append(Paragraph(
                f"<b>Effective Rate:</b> {best_option.get('percentage', 0)}%",
                self.styles['HighlightBox']
            ))
        else:
            story.append(Paragraph(
                "<b>No jurisdiction data available for comparison.</b>",
                self.styles['Normal']
            ))
        
        story.append(Spacer(1, 0.3 * inch))
        
        # Comparison Table
        story.append(Paragraph("Jurisdiction Comparison", self.styles['SectionHeader']))
        
        # Build comparison table
        table_data = [['Rank', 'Jurisdiction', 'Program', 'Rate', 'Estimated Credit']]
        for comp in comparisons:
            table_data.append([
                str(comp['rank']),
                comp['jurisdiction'],
                comp['ruleName'][:30] + '...' if len(comp['ruleName']) > 30 else comp['ruleName'],
                f"{comp['percentage']}%" if comp['percentage'] else 'N/A',
                f"${comp['estimatedCredit']:,.0f}"
            ])
        
        comp_table = Table(table_data, colWidths=[0.6*inch, 1.5*inch, 2.2*inch, 0.8*inch, 1.3*inch])
        comp_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c5aa0')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, 1), colors.HexColor('#e8f4f8')),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#cccccc')),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f8f8')])
        ]))
        story.append(comp_table)
        story.append(Spacer(1, 0.3 * inch))
        
        # Recommendations
        story.append(Paragraph("Recommendations", self.styles['SectionHeader']))
        
        # Only show recommendations if there's data
        if comparisons and len(comparisons) > 0 and best_option and best_option.get('jurisdiction'):
            savings = comparisons[0]['estimatedCredit'] - comparisons[-1]['estimatedCredit']
            story.append(Paragraph(
                f"â€¢ <b>Best Financial Option:</b> {best_option['jurisdiction']} offers the highest tax credit of ${best_option.get('estimatedCredit', 0):,.0f}",
                self.styles['Normal']
            ))
            story.append(Spacer(1, 6))
            story.append(Paragraph(
                f"â€¢ <b>Potential Savings:</b> Filming in {best_option['jurisdiction']} saves ${savings:,.0f} compared to the lowest option",
                self.styles['Normal']
            ))
            story.append(Spacer(1, 6))
            story.append(Paragraph(
                f"â€¢ <b>Next Steps:</b> Review compliance requirements for {best_option['jurisdiction']} and contact their film office to begin application process",
                self.styles['Normal']
            ))
        else:
            story.append(Paragraph(
                "â€¢ <b>No data available for recommendations.</b> Please provide jurisdiction comparison data.",
                self.styles['Normal']
            ))
        
        
        # Build PDF
        doc.build(story)
        buffer.seek(0)
        return buffer.getvalue()
    
    def generate_compliance_report(
        self,
        production_title: str,
        jurisdiction: str,
        rule_name: str,
        requirements: List[Dict[str, Any]],
        overall_status: str,
        estimated_credit: float
    ) -> bytes:
        """Generate compliance verification report"""
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=18
        )
        
        story = []
        
        # Title
        story.append(Paragraph("Tax Incentive Compliance Report", self.styles['CustomTitle']))
        story.append(Paragraph(
            f"Generated on {datetime.now().strftime('%B %d, %Y')}",
            self.styles['CustomSubtitle']
        ))
        story.append(Spacer(1, 0.5 * inch))
        
        # Production Info
        story.append(Paragraph("Production & Program Details", self.styles['SectionHeader']))
        info_data = [
            ['Production:', production_title],
            ['Jurisdiction:', jurisdiction],
            ['Program:', rule_name],
            ['Analysis Date:', datetime.now().strftime('%B %d, %Y')]
        ]
        info_table = Table(info_data, colWidths=[2*inch, 4*inch])
        info_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        story.append(info_table)
        story.append(Spacer(1, 0.3 * inch))
        
        # Compliance Status
        story.append(Paragraph("Compliance Status", self.styles['SectionHeader']))
        status_color = colors.HexColor('#28a745') if overall_status == 'compliant' else colors.HexColor('#dc3545')
        status_text = 'âœ“ COMPLIANT' if overall_status == 'compliant' else 'âœ— NON-COMPLIANT'
        story.append(Paragraph(
            f"<b><font color='{status_color.hexval()}'>{status_text}</font></b>",
            self.styles['HighlightBox']
        ))
        
        if overall_status == 'compliant' and estimated_credit:
            story.append(Paragraph(
                f"<b>Estimated Tax Credit:</b> ${estimated_credit:,.0f}",
                self.styles['HighlightBox']
            ))
        story.append(Spacer(1, 0.3 * inch))
        
        # Requirements Checklist
        story.append(Paragraph("Requirements Checklist", self.styles['SectionHeader']))
        
        req_data = [['Status', 'Requirement', 'Details']]
        for req in requirements:
            status_symbol = 'âœ“' if req['status'] == 'met' else ('?' if req['status'] == 'unknown' else 'âœ—')
            status_color = (colors.HexColor('#28a745') if req['status'] == 'met' else 
                          (colors.HexColor('#ffc107') if req['status'] == 'unknown' else colors.HexColor('#dc3545')))
            
            req_data.append([
                status_symbol,
                req['requirement'].replace('_', ' ').title(),
                req['description']
            ])
        
        req_table = Table(req_data, colWidths=[0.6*inch, 2*inch, 3.8*inch])
        req_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c5aa0')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#cccccc')),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('ALIGN', (0, 1), (0, -1), 'CENTER'),
        ]))
        story.append(req_table)
        
        # Build PDF
        doc.build(story)
        buffer.seek(0)
        return buffer.getvalue()
    
    def generate_scenario_report(
        self,
        production_title: str,
        jurisdiction: str,
        base_budget: float,
        scenarios: List[Dict[str, Any]],
        best_scenario: Dict[str, Any]
    ) -> bytes:
        """Generate scenario analysis report"""
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=18
        )
        
        story = []
        
        # Title
        story.append(Paragraph("Production Scenario Analysis", self.styles['CustomTitle']))
        story.append(Paragraph(
            f"Generated on {datetime.now().strftime('%B %d, %Y')}",
            self.styles['CustomSubtitle']
        ))
        story.append(Spacer(1, 0.5 * inch))
        
        # Overview
        story.append(Paragraph("Analysis Overview", self.styles['SectionHeader']))
        overview_data = [
            ['Production:', production_title],
            ['Jurisdiction:', jurisdiction],
            ['Base Budget:', f'${base_budget:,.0f}'],
            ['Scenarios Analyzed:', str(len(scenarios))]
        ]
        overview_table = Table(overview_data, colWidths=[2*inch, 4*inch])
        overview_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        story.append(overview_table)
        story.append(Spacer(1, 0.3 * inch))
        
        # Best Scenario
        story.append(Paragraph("Optimal Scenario", self.styles['SectionHeader']))
        story.append(Paragraph(
            f"<b>Scenario:</b> {best_scenario['scenarioName']}",
            self.styles['HighlightBox']
        ))
        story.append(Paragraph(
            f"<b>Budget:</b> ${best_scenario['scenarioParams']['budget']:,.0f}",
            self.styles['HighlightBox']
        ))
        story.append(Paragraph(
            f"<b>Estimated Credit:</b> ${best_scenario['estimatedCredit']:,.0f} ({best_scenario['effectiveRate']:.1f}%)",
            self.styles['HighlightBox']
        ))
        story.append(Spacer(1, 0.3 * inch))
        
        # Scenario Comparison
        story.append(Paragraph("Scenario Comparison", self.styles['SectionHeader']))
        
        scenario_data = [['Scenario', 'Budget', 'Tax Credit', 'Effective Rate', 'Program']]
        for scenario in scenarios:
            scenario_data.append([
                scenario['scenarioName'],
                f"${scenario['scenarioParams']['budget']:,.0f}",
                f"${scenario['estimatedCredit']:,.0f}",
                f"{scenario['effectiveRate']:.1f}%",
                scenario['bestRuleName'][:25] + '...' if len(scenario['bestRuleName']) > 25 else scenario['bestRuleName']
            ])
        
        scenario_table = Table(scenario_data, colWidths=[1.4*inch, 1.2*inch, 1.2*inch, 1*inch, 1.6*inch])
        scenario_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c5aa0')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, 1), colors.HexColor('#e8f4f8')),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#cccccc')),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        story.append(scenario_table)
        story.append(Spacer(1, 0.3 * inch))
        
        # Insights
        story.append(Paragraph("Key Insights", self.styles['SectionHeader']))
        worst_scenario = scenarios[-1]
        savings = best_scenario['estimatedCredit'] - worst_scenario['estimatedCredit']
        
        story.append(Paragraph(
            f"â€¢ <b>Optimization Potential:</b> ${savings:,.0f} difference between best and worst scenarios",
            self.styles['Normal']
        ))
        story.append(Spacer(1, 6))
        story.append(Paragraph(
            f"â€¢ <b>Budget Efficiency:</b> {best_scenario['scenarioName']} offers the highest return on investment",
            self.styles['Normal']
        ))
        story.append(Spacer(1, 6))
        story.append(Paragraph(
            f"â€¢ <b>Recommendation:</b> Consider {best_scenario['scenarioName']} for maximum tax incentive benefit",
            self.styles['Normal']
        ))
        
        # Build PDF
        doc.build(story)
        buffer.seek(0)
        return buffer.getvalue()


# Global PDF generator instance
pdf_generator = PDFReportGenerator()

