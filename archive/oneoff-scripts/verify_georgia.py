"""Verify Georgia jurisdiction and program in database."""
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from app.db.session import SessionLocal
from app.models.jurisdiction import Jurisdiction
from app.models.program import Program
import json

def verify():
    db = SessionLocal()
    
    try:
        # Check for Georgia jurisdiction
        georgia = db.query(Jurisdiction).filter(
            Jurisdiction.name == "Georgia"
        ).first()
        
        if not georgia:
            print("❌ Georgia jurisdiction not found!")
            return
        
        print(f"✅ Found Georgia jurisdiction:")
        print(f"   ID: {georgia.id}")
        print(f"   Name: {georgia.name}")
        print(f"   Type: {georgia.type}")
        print()
        
        # Check for Georgia program
        program = db.query(Program).filter(
            Program.jurisdiction_id == georgia.id
        ).first()
        
        if not program:
            print("❌ Georgia program not found!")
            return
        
        print(f"✅ Found Georgia program:")
        print(f"   ID: {program.id}")
        print(f"   Name: {program.name}")
        print(f"   Active: {program.active}")
        print()
        
        # Parse and display rules
        if program.rules:
            rules = json.loads(program.rules)
            print(f"📋 Program Rules Summary:")
            print(f"   Base Credit Rate: {rules.get('base_credit_rate', 0) * 100}%")
            print(f"   Qualified Categories: {len(rules.get('qualified_expenditure_categories', []))}")
            print(f"   Bonus Conditions: {len(rules.get('bonus_conditions', []))}")
            print(f"   Checklist Items: {len(rules.get('checklist', []))}")
            print(f"   Sunset Date: {rules.get('sunset_date', 'N/A')}")
            print()
            print("✅ All data verified successfully!")
        else:
            print("⚠️  Program has no rules defined")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    verify()
