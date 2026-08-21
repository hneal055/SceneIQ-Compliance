# create_maximizer.ps1
$ProjectPath = "C:\Projects\Tax_Incentive_Compliance_Platform"

Write-Host "Creating Maximizer files in: $ProjectPath" -ForegroundColor Green

# File 1: maximizer.py
$MaximizerPy = @"
"""
SceneIQ Maximizer Engine
"""
import os
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

@dataclass
class ApplicableRule:
    jurisdiction_id: str
    jurisdiction_name: str
    jurisdiction_type: str
    rule_key: str
    rule_type: str
    value: Optional[float]
    value_unit: str
    inheritance_mode: str
    conflict_priority: int
    source_citation: str
    effective_date: datetime

@dataclass
class MaximizedResult:
    total_value: float
    total_value_unit: str
    breakdown: Dict[str, float]
    applied_rules: List[ApplicableRule]
    overridden_rules: List[ApplicableRule]
    conflicts_resolved: List[str]
    warnings: List[str]
    recommendations: List[str]

class SceneIQMaximizer:
    def __init__(self, db_url: str = None):
        self.db_url = db_url or os.getenv("DATABASE_URL")
        if not self.db_url:
            raise ValueError("DATABASE_URL not set")
    
    def get_connection(self):
        return psycopg2.connect(self.db_url)
    
    def resolve_jurisdiction_layers(self, lat: float, lng: float) -> List[Dict]:
        conn = self.get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        try:
            cur.execute("""
                SELECT id, name, type, level, parent_jurisdiction_id
                FROM jurisdictions
                WHERE ST_Contains(geometry, ST_SetSRID(ST_MakePoint(%s, %s), 4326))
                ORDER BY level ASC
            """, (lng, lat))
            results = cur.fetchall()
            if results:
                cur.close()
                conn.close()
                return results
        except Exception as e:
            logger.debug(f"Spatial query failed: {e}")
        
        cur.execute("""
            SELECT id, name, type, level, parent_jurisdiction_id
            FROM jurisdictions
            WHERE active = true
            ORDER BY level ASC
        """)
        results = cur.fetchall()
        cur.close()
        conn.close()
        return results
    
    def fetch_applicable_rules(self, jurisdiction_ids: List[str], project_type: str) -> List[ApplicableRule]:
        if not jurisdiction_ids:
            return []
        
        conn = self.get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        placeholders = ','.join(['%s'] * len(jurisdiction_ids))
        cur.execute(f"""
            SELECT 
                lr.jurisdiction_id,
                j.name as jurisdiction_name,
                j.type as jurisdiction_type,
                lr.rule_key,
                lr.rule_type,
                lr.value,
                lr.value_unit,
                COALESCE(ip.inheritance_mode, 'additive') as inheritance_mode,
                COALESCE(ip.conflict_priority, 10) as conflict_priority,
                lr.source_citation,
                lr.effective_date
            FROM local_rules lr
            JOIN jurisdictions j ON lr.jurisdiction_id = j.id
            LEFT JOIN inheritance_policies ip 
                ON ip.jurisdiction_id = lr.jurisdiction_id 
                AND ip.rule_category = (
                    CASE lr.rule_type
                        WHEN 'tax_abatement' THEN 'incentives'
                        WHEN 'green_bonus' THEN 'incentives'
                        WHEN 'permit_fee' THEN 'fees'
                        ELSE 'other'
                    END
                )
            WHERE lr.jurisdiction_id IN ({placeholders})
                AND (lr.expiry_date IS NULL OR lr.expiry_date > NOW())
                AND (lr.effective_date <= NOW())
                AND (lr.applies_to::jsonb ? %s OR lr.applies_to::jsonb ? 'all')
            ORDER BY j.level ASC, ip.conflict_priority ASC
        """, jurisdiction_ids + [project_type])
        
        rules = cur.fetchall()
        cur.close()
        conn.close()
        
        return [
            ApplicableRule(
                jurisdiction_id=r['jurisdiction_id'],
                jurisdiction_name=r['jurisdiction_name'],
                jurisdiction_type=r['jurisdiction_type'],
                rule_key=r['rule_key'],
                rule_type=r['rule_type'],
                value=r['value'],
                value_unit=r['value_unit'] or 'USD',
                inheritance_mode=r['inheritance_mode'],
                conflict_priority=r['conflict_priority'],
                source_citation=r['source_citation'],
                effective_date=r['effective_date']
            )
            for r in rules
        ]
    
    def apply_inheritance_logic(self, rules: List[ApplicableRule]) -> Tuple[List[ApplicableRule], List[ApplicableRule]]:
        applied = []
        overridden = []
        
        rules_by_key: Dict[str, List[ApplicableRule]] = {}
        for rule in rules:
            if rule.rule_key not in rules_by_key:
                rules_by_key[rule.rule_key] = []
            rules_by_key[rule.rule_key].append(rule)
        
        for rule_key, rule_group in rules_by_key.items():
            rule_group.sort(key=lambda x: (
                0 if x.jurisdiction_type == 'state' else
                1 if x.jurisdiction_type == 'county' else
                2 if x.jurisdiction_type in ['city', 'town'] else 3,
                x.conflict_priority
            ))
            
            current_rule = None
            for rule in rule_group:
                if current_rule is None:
                    current_rule = rule
                    continue
                
                if rule.inheritance_mode == 'strict':
                    overridden.append(rule)
                elif rule.inheritance_mode == 'override':
                    overridden.append(current_rule)
                    current_rule = rule
                elif rule.inheritance_mode == 'additive':
                    if current_rule.value is not None and rule.value is not None:
                        if current_rule.value_unit == rule.value_unit:
                            current_rule.value += rule.value
                            applied.append(rule)
                        else:
                            applied.append(current_rule)
                            applied.append(rule)
                            current_rule = None
                    else:
                        applied.append(rule)
                else:
                    applied.append(rule)
            
            if current_rule:
                applied.append(current_rule)
        
        return applied, overridden
    
    def calculate_net_value(self, applied_rules: List[ApplicableRule]) -> Dict[str, float]:
        breakdown = {
            'tax_abatement': 0.0,
            'green_bonus': 0.0,
            'permit_fee': 0.0,
            'other': 0.0
        }
        
        for rule in applied_rules:
            category = rule.rule_type
            value = rule.value or 0.0
            if category == 'permit_fee':
                value = -abs(value)
            if category in breakdown:
                breakdown[category] += value
            else:
                breakdown['other'] += value
        
        return breakdown
    
    def maximize(self, lat: float, lng: float, project_type: str = 'all') -> MaximizedResult:
        jurisdictions = self.resolve_jurisdiction_layers(lat, lng)
        jurisdiction_ids = [j['id'] for j in jurisdictions]
        
        if not jurisdiction_ids:
            return MaximizedResult(
                total_value=0.0, total_value_unit='USD', breakdown={},
                applied_rules=[], overridden_rules=[], conflicts_resolved=[],
                warnings=['No jurisdictions found'], recommendations=[]
            )
        
        all_rules = self.fetch_applicable_rules(jurisdiction_ids, project_type)
        
        if not all_rules:
            return MaximizedResult(
                total_value=0.0, total_value_unit='USD', breakdown={},
                applied_rules=[], overridden_rules=[],
                conflicts_resolved=['No active rules found'],
                warnings=['Run monitor.py to populate local_rules'],
                recommendations=['Ensure monitor has been executed']
            )
        
        applied_rules, overridden_rules = self.apply_inheritance_logic(all_rules)
        breakdown = self.calculate_net_value(applied_rules)
        total_value = sum(v for v in breakdown.values())
        
        conflicts_resolved = [f"{r.jurisdiction_name} {r.rule_key} overridden" for r in overridden_rules]
        warnings = []
        if breakdown.get('permit_fee', 0) < 0:
            warnings.append(f"Net fees of ${-breakdown['permit_fee']:.2f} reduce incentive value")
        
        return MaximizedResult(
            total_value=total_value, total_value_unit='USD', breakdown=breakdown,
            applied_rules=applied_rules, overridden_rules=overridden_rules,
            conflicts_resolved=conflicts_resolved, warnings=warnings,
            recommendations=['Compare nearby jurisdictions for better incentives']
        )

def main():
    import sys
    import json
    
    logging.basicConfig(level=logging.INFO)
    
    if len(sys.argv) < 3:
        print("Usage: python maximizer.py <lat> <lng> [project_type]")
        sys.exit(1)
    
    lat = float(sys.argv[1])
    lng = float(sys.argv[2])
    project_type = sys.argv[3] if len(sys.argv) > 3 else 'all'
    
    maximizer = SceneIQMaximizer()
    result = maximizer.maximize(lat, lng, project_type)
    
    print(json.dumps({
        'total_value': result.total_value,
        'total_value_unit': result.total_value_unit,
        'breakdown': result.breakdown,
        'warnings': result.warnings,
        'recommendations': result.recommendations
    }, indent=2))

if __name__ == "__main__":
    main()
"@

# Write the maximizer.py file
Set-Content -Path "$ProjectPath\maximizer.py" -Value $MaximizerPy -Encoding UTF8
Write-Host "Created: maximizer.py" -ForegroundColor Green

# File 2: test_maximizer.py
$TestMaximizerPy = @"
from maximizer import SceneIQMaximizer

def test_maximizer():
    maximizer = SceneIQMaximizer()
    result = maximizer.maximize(42.8864, -78.8784, "solar")
    
    print("\n" + "="*60)
    print("PILOTFORGE MAXIMIZER RESULT")
    print("="*60)
    print(f"Total Value: \${result.total_value:.2f} {result.total_value_unit}")
    print(f"\nBreakdown:")
    for category, value in result.breakdown.items():
        if value != 0:
            print(f"  {category}: \${value:.2f}")
    
    if result.warnings:
        print(f"\nWarnings:")
        for w in result.warnings:
            print(f"  ⚠ {w}")

if __name__ == "__main__":
    test_maximizer()
"@

Set-Content -Path "$ProjectPath\test_maximizer.py" -Value $TestMaximizerPy -Encoding UTF8
Write-Host "Created: test_maximizer.py" -ForegroundColor Green

Write-Host ""
Write-Host "Done! Now run: python test_maximizer.py" -ForegroundColor Yellow
