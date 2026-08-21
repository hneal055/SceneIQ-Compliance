import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

try:
    conn = psycopg2.connect(os.getenv('DATABASE_URL'))
    conn.autocommit = True
    cur = conn.cursor()
    
    print("Checking database...")
    
    # Check connection
    cur.execute('SELECT 1')
    print("✓ Database connected")
    
    # Get column names from jurisdictions table
    cur.execute("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'jurisdictions'
        ORDER BY ordinal_position
    """)
    columns = [row[0] for row in cur.fetchall()]
    print(f"✓ Jurisdictions table columns: {', '.join(columns[:10])}...")
    
    # Count records
    cur.execute('SELECT COUNT(*) FROM jurisdictions')
    count = cur.fetchone()[0]
    print(f"✓ Number of jurisdiction records: {count}")
    
    # Show sample jurisdictions (using available columns)
    cur.execute('SELECT id, name, type FROM jurisdictions LIMIT 5')
    rows = cur.fetchall()
    print("\nSample jurisdictions:")
    for row in rows:
        print(f"  - {row[1]} (type: {row[2]})")
    
    # Check local_rules table
    cur.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_name = 'local_rules'
        )
    """)
    local_rules_exists = cur.fetchone()[0]
    print(f"\n✓ local_rules table exists: {local_rules_exists}")
    
    if local_rules_exists:
        cur.execute('SELECT COUNT(*) FROM local_rules')
        rule_count = cur.fetchone()[0]
        print(f"✓ Number of local_rules records: {rule_count}")
    
    # Check inheritance_policies table
    cur.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_name = 'inheritance_policies'
        )
    """)
    policies_exists = cur.fetchone()[0]
    print(f"✓ inheritance_policies table exists: {policies_exists}")
    
    cur.close()
    conn.close()
    
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()
