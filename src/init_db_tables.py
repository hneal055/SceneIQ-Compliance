import psycopg2
from psycopg2 import sql

def init_database_tables():
    """Initialize database tables for Tax Incentive Compliance Platform"""
    
    connection = None
    try:
        # Connect to the database
        connection = psycopg2.connect(
            host="localhost",
            port=5432,
            database="tax_incentive_db",
            user="postgres",
            password="postgres"
        )
        connection.autocommit = False
        cursor = connection.cursor()
        
        print("âœ… Connected to database successfully")
        
        # Create tables if they don't exist
        tables_sql = [
            """
            CREATE TABLE IF NOT EXISTS clients (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                tax_id VARCHAR(50) UNIQUE,
                industry VARCHAR(100),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS incentives (
                id SERIAL PRIMARY KEY,
                client_id INTEGER REFERENCES clients(id),
                incentive_name VARCHAR(255) NOT NULL,
                incentive_type VARCHAR(100),
                amount DECIMAL(15, 2),
                status VARCHAR(50) DEFAULT 'pending',
                application_date DATE,
                approval_date DATE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS compliance_reports (
                id SERIAL PRIMARY KEY,
                client_id INTEGER REFERENCES clients(id),
                report_period VARCHAR(50),
                report_date DATE DEFAULT CURRENT_DATE,
                total_incentives DECIMAL(15, 2),
                compliance_status VARCHAR(50),
                pdf_path VARCHAR(500),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS expenses (
                id SERIAL PRIMARY KEY,
                client_id INTEGER REFERENCES clients(id),
                expense_type VARCHAR(100),
                amount DECIMAL(15, 2),
                description TEXT,
                date_incurred DATE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        ]
        
        for i, table_sql in enumerate(tables_sql):
            cursor.execute(table_sql)
            print(f"âœ… Created/verified table {i+1}")
        
        # Commit the transaction
        connection.commit()
        print("âœ… Database tables initialized successfully")
        
        # Insert sample data
        sample_data_sql = """
        INSERT INTO clients (name, tax_id, industry) 
        VALUES 
            ('ABC Film Productions', '12-3456789', 'Film & Entertainment'),
            ('XYZ Media Studios', '98-7654321', 'Media Production'),
            ('Digital Effects Inc', '45-6789012', 'Visual Effects')
        ON CONFLICT (tax_id) DO NOTHING;
        """
        
        cursor.execute(sample_data_sql)
        print("âœ… Inserted sample client data")
        
        connection.commit()
        cursor.close()
        
    except (Exception, psycopg2.DatabaseError) as error:
        print(f"âŒ Error: {error}")
        if connection:
            connection.rollback()
    finally:
        if connection:
            connection.close()
            print("âœ… Database connection closed")

if __name__ == "__main__":
    init_database_tables()
