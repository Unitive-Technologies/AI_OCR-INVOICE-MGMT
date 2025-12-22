
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
    print("\nYou can now use:")
    print("  SELECT * FROM invoices_summary;")
    print("  SELECT * FROM invoices_detail;")
    print("  SELECT * FROM invoices_extended;")


if __name__ == "__main__":
    create_views()
