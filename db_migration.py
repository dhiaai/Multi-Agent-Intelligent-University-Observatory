import sqlite3
from sqlalchemy import create_engine
from db_setup import _build_engine, DB_NAME, SQLITE_URL

def migrate():
    engine = _build_engine()
    
    # We will use raw SQL to avoid depending on ORM states
    if str(engine.url).startswith("sqlite"):
        print(f"Applying migration to SQLite at {SQLITE_URL}")
        try:
            with engine.connect() as conn:
                conn.exec_driver_sql("ALTER TABLE opportunities ADD COLUMN tags TEXT;")
                conn.commit()
            print("Successfully added 'tags' column to 'opportunities' table.")
        except Exception as e:
            if "duplicate column name" in str(e).lower():
                print("'tags' column already exists in 'opportunities' table.")
            else:
                print(f"Error during migration: {e}")
    else:
        print(f"Applying migration to PostgreSQL at {DB_NAME}")
        try:
            with engine.connect() as conn:
                conn.exec_driver_sql("ALTER TABLE opportunities ADD COLUMN tags TEXT;")
                conn.commit()
            print("Successfully added 'tags' column to 'opportunities' table.")
        except Exception as e:
            if "column \"tags\" of relation \"opportunities\" already exists" in str(e).lower():
                print("'tags' column already exists in 'opportunities' table.")
            else:
                print(f"Error during migration: {e}")

if __name__ == "__main__":
    migrate()
