
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg://docai:docai@localhost:5432/docai",
)


def create_views():
    """Create PostgreSQL views for invoices."""
    engine = create_engine(DATABASE_URL)

    # Read the SQL file
    sql_file = os.path.join(os.path.dirname(__file__), "db_views.sql")

    with open(sql_file, "r") as f:
        sql_commands = f.read()

    with engine.connect() as conn:
        # Execute each statement separately
        for statement in sql_commands.split(';'):
            statement = statement.strip()
            if statement:
                try:
                    conn.execute(text(statement))
                    conn.commit()
                    print(f"✓ Executed: {statement[:50]}...")
                except Exception as e:
                    print(f"✗ Error: {e}")
                    conn.rollback()

    print("\n✅ Views created successfully!")
    print("\nYou can now use convenient views, for example:")
    print("  -- Invoices")
    print("  SELECT * FROM invoices_summary LIMIT 20;")
    print("  SELECT * FROM invoices_detail LIMIT 5;")
    print("  SELECT * FROM invoices_extended LIMIT 20;")
    print("\n  -- Core tables")
    print("  SELECT * FROM documents_view LIMIT 20;")
    print("  SELECT * FROM ocr_results_view LIMIT 20;")
    print("  SELECT * FROM document_classifications_view LIMIT 20;")
    print("  SELECT * FROM document_processing_view LIMIT 20;")
    print("  SELECT * FROM receipts_view LIMIT 20;")
    print("  SELECT * FROM purchase_orders_view LIMIT 20;")
    print("  SELECT * FROM extraction_results_view LIMIT 20;")
    print("\n  -- Pretty JSON for non-invoice raw_metadata")
    print("  SELECT * FROM receipts_detail LIMIT 5;")
    print("  SELECT * FROM purchase_orders_detail LIMIT 5;")
    print("  SELECT * FROM extraction_results_detail LIMIT 5;")


if __name__ == "__main__":
    create_views()
