"""
FORCE RESET DATABASE - COMPLETE CLEAN REBUILD
WARNING: This will DELETE ALL EXISTING DATA and recreate the database from scratch
"""
import psycopg2
import sys
from psycopg2 import sql
import time

def drop_and_recreate_database():
    """Completely drop and recreate the database"""
    print("=" * 60)
    print("âš ï¸  DATABASE FORCE RESET - ALL DATA WILL BE LOST!")
    print("=" * 60)
    
    # Get confirmation
    confirm = input("Are you sure you want to DELETE ALL DATA and recreate? (type 'YES' to confirm): ")
    if confirm != "YES":
        print("âŒ Operation cancelled")
        return False
    
    print("\nðŸš€ Starting complete database reset...")
    
    # Connection parameters
    db_params = {
        "host": "localhost",
        "port": 5432,
        "user": "postgres",
        "password": "postgres"
    }
    
    connection = None
    try:
        # Step 1: Connect to PostgreSQL server (without database)
        print("\n1. Connecting to PostgreSQL server...")
        connection = psycopg2.connect(**db_params)
        connection.autocommit = True  # Required for dropping/creating databases
        cursor = connection.cursor()
        
        # Step 2: Terminate existing connections to the database
        print("2. Terminating existing connections...")
        cursor.execute("""
            SELECT pg_terminate_backend(pid) 
            FROM pg_stat_activity 
            WHERE datname = 'tax_incentive_db' 
            AND pid <> pg_backend_pid();
        """)
        
        # Step 3: Drop the database if it exists
        print("3. Dropping database if exists...")
        cursor.execute("DROP DATABASE IF EXISTS tax_incentive_db;")
        print("   âœ… Database dropped")
        
        # Step 4: Create a fresh database
        print("4. Creating new database...")
        cursor.execute("CREATE DATABASE tax_incentive_db;")
        print("   âœ… Database created")
        
        cursor.close()
        connection.close()
        
        # Step 5: Wait a moment
        time.sleep(2)
        
        # Step 6: Connect to the new database and create tables
        print("5. Connecting to new database...")
        db_params["database"] = "tax_incentive_db"
        connection = psycopg2.connect(**db_params)
        connection.autocommit = False
        cursor = connection.cursor()
        
        print("6. Creating tables...")
        
        # ========== CREATE ALL TABLES ==========
        
        # Clients table
        cursor.execute("""
            CREATE TABLE clients (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                tax_id VARCHAR(50) UNIQUE NOT NULL,
                industry VARCHAR(100),
                contact_person VARCHAR(100),
                email VARCHAR(255),
                phone VARCHAR(50),
                address TEXT,
                city VARCHAR(100),
                state VARCHAR(50),
                zip_code VARCHAR(20),
                country VARCHAR(100) DEFAULT 'USA',
                status VARCHAR(50) DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                notes TEXT
            )
        """)
        print("   âœ… Created 'clients' table")
        
        # Incentives table
        cursor.execute("""
            CREATE TABLE incentives (
                id SERIAL PRIMARY KEY,
                client_id INTEGER NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
                incentive_name VARCHAR(255) NOT NULL,
                incentive_type VARCHAR(100) NOT NULL,
                jurisdiction VARCHAR(100),
                program_code VARCHAR(50),
                description TEXT,
                amount DECIMAL(15, 2) NOT NULL,
                eligible_amount DECIMAL(15, 2),
                claimed_amount DECIMAL(15, 2),
                application_number VARCHAR(100),
                application_date DATE,
                approval_date DATE,
                start_date DATE,
                end_date DATE,
                status VARCHAR(50) DEFAULT 'pending',
                compliance_rating VARCHAR(20),
                risk_level VARCHAR(20) DEFAULT 'low',
                documents_attached BOOLEAN DEFAULT FALSE,
                created_by VARCHAR(100),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                CONSTRAINT check_amounts CHECK (claimed_amount <= amount),
                CONSTRAINT check_dates CHECK (start_date <= end_date)
            )
        """)
        print("   âœ… Created 'incentives' table")
        
        # Compliance Reports table
        cursor.execute("""
            CREATE TABLE compliance_reports (
                id SERIAL PRIMARY KEY,
                client_id INTEGER NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
                report_name VARCHAR(255) NOT NULL,
                report_period VARCHAR(50),
                report_year INTEGER,
                quarter VARCHAR(10),
                report_date DATE DEFAULT CURRENT_DATE,
                generated_by VARCHAR(100),
                total_eligible_incentives DECIMAL(15, 2) DEFAULT 0,
                total_claimed_incentives DECIMAL(15, 2) DEFAULT 0,
                compliance_score DECIMAL(5, 2),
                compliance_status VARCHAR(50) DEFAULT 'pending_review',
                audit_flag BOOLEAN DEFAULT FALSE,
                audit_notes TEXT,
                pdf_path VARCHAR(500),
                excel_path VARCHAR(500),
                is_finalized BOOLEAN DEFAULT FALSE,
                finalized_by VARCHAR(100),
                finalized_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        print("   âœ… Created 'compliance_reports' table")
        
        # Expenses table
        cursor.execute("""
            CREATE TABLE expenses (
                id SERIAL PRIMARY KEY,
                client_id INTEGER NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
                incentive_id INTEGER REFERENCES incentives(id) ON DELETE SET NULL,
                expense_type VARCHAR(100) NOT NULL,
                expense_category VARCHAR(100),
                description TEXT,
                amount DECIMAL(15, 2) NOT NULL,
                currency VARCHAR(10) DEFAULT 'USD',
                date_incurred DATE NOT NULL,
                invoice_number VARCHAR(100),
                vendor_name VARCHAR(255),
                is_eligible BOOLEAN DEFAULT TRUE,
                eligibility_notes TEXT,
                documents_attached BOOLEAN DEFAULT FALSE,
                created_by VARCHAR(100),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                CONSTRAINT positive_amount CHECK (amount > 0)
            )
        """)
        print("   âœ… Created 'expenses' table")
        
        # Documents table
        cursor.execute("""
            CREATE TABLE documents (
                id SERIAL PRIMARY KEY,
                client_id INTEGER NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
                incentive_id INTEGER REFERENCES incentives(id) ON DELETE SET NULL,
                document_name VARCHAR(255) NOT NULL,
                document_type VARCHAR(100),
                file_path VARCHAR(500) NOT NULL,
                file_type VARCHAR(50),
                file_size BIGINT,
                upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                uploaded_by VARCHAR(100),
                description TEXT,
                is_confidential BOOLEAN DEFAULT FALSE,
                tags TEXT[]
            )
        """)
        print("   âœ… Created 'documents' table")
        
        # Audit Log table
        cursor.execute("""
            CREATE TABLE audit_log (
                id SERIAL PRIMARY KEY,
                table_name VARCHAR(100) NOT NULL,
                record_id INTEGER NOT NULL,
                action VARCHAR(50) NOT NULL,
                old_data JSONB,
                new_data JSONB,
                changed_by VARCHAR(100),
                changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                ip_address VARCHAR(50),
                user_agent TEXT
            )
        """)
        print("   âœ… Created 'audit_log' table")
        
        # Users table (if not using external auth)
        cursor.execute("""
            CREATE TABLE users (
                id SERIAL PRIMARY KEY,
                username VARCHAR(100) UNIQUE NOT NULL,
                email VARCHAR(255) UNIQUE NOT NULL,
                full_name VARCHAR(255),
                role VARCHAR(50) DEFAULT 'analyst',
                department VARCHAR(100),
                is_active BOOLEAN DEFAULT TRUE,
                last_login TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                password_hash VARCHAR(255)
            )
        """)
        print("   âœ… Created 'users' table")
        
        # Create indexes for better performance
        print("7. Creating indexes...")
        
        indexes = [
            "CREATE INDEX idx_clients_tax_id ON clients(tax_id);",
            "CREATE INDEX idx_clients_status ON clients(status);",
            "CREATE INDEX idx_incentives_client_id ON incentives(client_id);",
            "CREATE INDEX idx_incentives_status ON incentives(status);",
            "CREATE INDEX idx_incentives_type ON incentives(incentive_type);",
            "CREATE INDEX idx_compliance_reports_client_id ON compliance_reports(client_id);",
            "CREATE INDEX idx_compliance_reports_period ON compliance_reports(report_period);",
            "CREATE INDEX idx_expenses_client_id ON expenses(client_id);",
            "CREATE INDEX idx_expenses_date ON expenses(date_incurred);",
            "CREATE INDEX idx_expenses_type ON expenses(expense_type);",
            "CREATE INDEX idx_documents_client_id ON documents(client_id);",
            "CREATE INDEX idx_audit_log_table_record ON audit_log(table_name, record_id);"
        ]
        
        for i, index_sql in enumerate(indexes, 1):
            cursor.execute(index_sql)
            print(f"   âœ… Created index {i}/{len(indexes)}")
        
        # Step 8: Insert comprehensive sample data
        print("\n8. Inserting comprehensive sample data...")
        
        # Insert sample users
        cursor.execute("""
            INSERT INTO users (username, email, full_name, role, department) 
            VALUES 
                ('admin', 'admin@taxincentive.com', 'System Administrator', 'admin', 'IT'),
                ('john.doe', 'john.doe@taxincentive.com', 'John Doe', 'manager', 'Compliance'),
                ('jane.smith', 'jane.smith@taxincentive.com', 'Jane Smith', 'analyst', 'Tax'),
                ('bob.wilson', 'bob.wilson@taxincentive.com', 'Bob Wilson', 'analyst', 'Audit')
            ON CONFLICT (username) DO NOTHING;
        """)
        print("   âœ… Inserted sample users")
        
        # Insert sample clients
        cursor.execute("""
            INSERT INTO clients (name, tax_id, industry, contact_person, email, phone, city, state, status) 
            VALUES 
                ('Paramount Pictures', '12-3456789', 'Film Production', 'Sarah Johnson', 'sarah@paramount.com', '(555) 123-4567', 'Hollywood', 'CA', 'active'),
                ('Disney Studios', '98-7654321', 'Entertainment', 'Michael Chen', 'michael@disney.com', '(555) 234-5678', 'Burbank', 'CA', 'active'),
                ('Netflix Productions', '45-6789012', 'Streaming Media', 'Jessica Williams', 'jessica@netflix.com', '(555) 345-6789', 'Los Gatos', 'CA', 'active'),
                ('Warner Bros.', '23-4567890', 'Film & TV', 'Robert Davis', 'robert@warner.com', '(555) 456-7890', 'Burbank', 'CA', 'active'),
                ('Universal Pictures', '34-5678901', 'Film Production', 'Emily Brown', 'emily@universal.com', '(555) 567-8901', 'Universal City', 'CA', 'active'),
                ('Sony Pictures', '56-7890123', 'Entertainment', 'David Miller', 'david@sony.com', '(555) 678-9012', 'Culver City', 'CA', 'active'),
                ('Amazon Studios', '67-8901234', 'Digital Media', 'Lisa Garcia', 'lisa@amazon.com', '(555) 789-0123', 'Seattle', 'WA', 'active'),
                ('Apple Studios', '78-9012345', 'Technology & Media', 'Kevin Lee', 'kevin@apple.com', '(555) 890-1234', 'Cupertino', 'CA', 'active'),
                ('Lionsgate Films', '89-0123456', 'Independent Film', 'Amanda Taylor', 'amanda@lionsgate.com', '(555) 901-2345', 'Santa Monica', 'CA', 'active'),
                ('A24 Films', '90-1234567', 'Independent Film', 'Daniel Moore', 'daniel@a24.com', '(555) 012-3456', 'New York', 'NY', 'active')
            ON CONFLICT (tax_id) DO NOTHING;
        """)
        print("   âœ… Inserted 10 sample clients")
        
        # Insert sample incentives
        cursor.execute("""
            INSERT INTO incentives (client_id, incentive_name, incentive_type, jurisdiction, amount, eligible_amount, claimed_amount, application_date, approval_date, status) 
            VALUES 
                (1, 'California Film Tax Credit', 'State Tax Credit', 'California', 2500000.00, 2500000.00, 1500000.00, '2024-01-15', '2024-02-20', 'approved'),
                (1, 'Federal Production Tax Deduction', 'Federal Deduction', 'Federal', 1800000.00, 1800000.00, 900000.00, '2024-02-10', NULL, 'pending'),
                (2, 'Georgia Entertainment Tax Credit', 'State Tax Credit', 'Georgia', 5000000.00, 5000000.00, 3000000.00, '2024-03-01', '2024-03-25', 'approved'),
                (2, 'Post-Production Incentive', 'Post-Production', 'California', 750000.00, 750000.00, 400000.00, '2024-01-20', '2024-02-15', 'approved'),
                (3, 'New York Film Tax Credit', 'State Tax Credit', 'New York', 3200000.00, 3200000.00, 2200000.00, '2024-02-05', NULL, 'under_review'),
                (3, 'Digital Media Production Credit', 'Digital Media', 'Federal', 1200000.00, 1200000.00, 800000.00, '2024-01-30', '2024-02-28', 'approved'),
                (4, 'Visual Effects Incentive', 'VFX Tax Credit', 'California', 950000.00, 950000.00, 600000.00, '2024-02-15', '2024-03-10', 'approved'),
                (5, 'Music Production Tax Credit', 'Music Credit', 'Tennessee', 1500000.00, 1500000.00, 750000.00, '2024-03-05', NULL, 'pending'),
                (6, 'International Co-Production', 'Co-Production', 'International', 2800000.00, 2800000.00, 1800000.00, '2024-02-20', '2024-03-18', 'approved'),
                (7, 'Rural Production Incentive', 'Rural Development', 'Georgia', 850000.00, 850000.00, 450000.00, '2024-01-25', '2024-02-22', 'approved'),
                (8, 'Technology Innovation Credit', 'R&D Credit', 'Federal', 2200000.00, 2200000.00, 1200000.00, '2024-03-10', NULL, 'pending'),
                (9, 'Independent Film Grant', 'Grant', 'California', 500000.00, 500000.00, 250000.00, '2024-02-28', '2024-03-20', 'approved'),
                (10, 'Diversity & Inclusion Credit', 'Diversity Credit', 'New York', 300000.00, 300000.00, 150000.00, '2024-03-15', NULL, 'under_review')
            ON CONFLICT DO NOTHING;
        """)
        print("   âœ… Inserted 13 sample incentives")
        
        # Insert sample expenses
        cursor.execute("""
            INSERT INTO expenses (client_id, incentive_id, expense_type, expense_category, description, amount, date_incurred, vendor_name, is_eligible) 
            VALUES 
                (1, 1, 'Production', 'Direct Costs', 'Location fees for film shoot', 250000.00, '2024-01-20', 'Location Management Inc', TRUE),
                (1, 1, 'Labor', 'Cast & Crew', 'Lead actor compensation', 500000.00, '2024-01-25', 'Talent Agency LLC', TRUE),
                (1, 2, 'Equipment', 'Production Equipment', 'Camera and lighting rental', 150000.00, '2024-02-05', 'Camera Rentals Co', TRUE),
                (2, 3, 'Post-Production', 'VFX & Editing', 'Visual effects work', 750000.00, '2024-03-10', 'VFX Studio Inc', TRUE),
                (2, 4, 'Music', 'Sound Production', 'Original score composition', 200000.00, '2024-03-15', 'Music Productions Ltd', TRUE),
                (3, 5, 'Marketing', 'Promotion', 'Digital marketing campaign', 300000.00, '2024-02-20', 'Marketing Agency', FALSE),
                (4, 7, 'Labor', 'VFX Artists', 'VFX team salaries', 450000.00, '2024-02-28', 'VFX Talent Agency', TRUE),
                (5, 8, 'Travel', 'Production Travel', 'Location scouting travel', 75000.00, '2024-03-01', 'Travel Services Co', TRUE),
                (6, 9, 'Legal', 'Production Legal', 'Contract legal services', 120000.00, '2024-03-05', 'Legal Firm LLP', TRUE),
                (7, 10, 'Infrastructure', 'Rural Development', 'Temporary infrastructure setup', 250000.00, '2024-02-15', 'Construction Services', TRUE)
            ON CONFLICT DO NOTHING;
        """)
        print("   âœ… Inserted 10 sample expenses")
        
        # Insert sample compliance reports
        cursor.execute("""
            INSERT INTO compliance_reports (client_id, report_name, report_period, report_year, quarter, total_eligible_incentives, total_claimed_incentives, compliance_score, compliance_status) 
            VALUES 
                (1, 'Q1 2024 Compliance Report', 'Q1', 2024, 'Q1', 4300000.00, 2400000.00, 92.5, 'compliant'),
                (2, 'Q1 2024 Compliance Report', 'Q1', 2024, 'Q1', 5750000.00, 3400000.00, 88.2, 'compliant'),
                (3, 'Q1 2024 Compliance Report', 'Q1', 2024, 'Q1', 4400000.00, 3000000.00, 85.7, 'needs_review'),
                (4, 'Q1 2024 Compliance Report', 'Q1', 2024, 'Q1', 950000.00, 600000.00, 95.0, 'compliant'),
                (5, 'Q1 2024 Compliance Report', 'Q1', 2024, 'Q1', 1500000.00, 750000.00, 76.3, 'non_compliant')
            ON CONFLICT DO NOTHING;
        """)
        print("   âœ… Inserted 5 sample compliance reports")
        
        # Commit all changes
        connection.commit()
        
        print("\n" + "=" * 60)
        print("âœ… DATABASE RESET COMPLETE!")
        print("=" * 60)
        
        # Display summary
        cursor.execute("SELECT COUNT(*) as count FROM clients")
        clients = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) as count FROM incentives")
        incentives = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) as count FROM expenses")
        expenses = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) as count FROM compliance_reports")
        reports = cursor.fetchone()[0]
        
        print(f"\nðŸ“Š Database Summary:")
        print(f"   â€¢ Clients: {clients}")
        print(f"   â€¢ Incentives: {incentives}")
        print(f"   â€¢ Expenses: {expenses}")
        print(f"   â€¢ Compliance Reports: {reports}")
        
        cursor.close()
        connection.close()
        
        return True
        
    except Exception as e:
        print(f"\nâŒ ERROR: {e}")
        print("\nðŸ”§ Troubleshooting steps:")
        print("   1. Make sure PostgreSQL is running")
        print("   2. Check if Docker container 'tax-incentive-db' is running")
        print("   3. Verify credentials in the script")
        print("   4. Check if port 5432 is correct")
        
        if connection:
            connection.rollback()
            connection.close()
        
        return False

if __name__ == "__main__":
    # Check if psycopg2 is installed
    try:
        import psycopg2
    except ImportError:
        print("âŒ psycopg2-binary is not installed")
        print("   Install it with: pip install psycopg2-binary")
        sys.exit(1)
    
    # Run the reset
    success = drop_and_recreate_database()
    
    if success:
        print("\nðŸŽ‰ Database is ready for the Tax Incentive Compliance Platform!")
        print("\nðŸ”— Connection Details:")
        print("   Host: localhost")
        print("   Port: 5432")
        print("   Database: tax_incentive_db")
        print("   Username: postgres")
        print("   Password: postgres")
        print("\nðŸš€ Next steps:")
        print("   1. Restart your FastAPI application")
        print("   2. Visit http://localhost:8000/docs")
        print("   3. Start using the platform!")
    else:
        print("\nâŒ Database reset failed")
        sys.exit(1)


