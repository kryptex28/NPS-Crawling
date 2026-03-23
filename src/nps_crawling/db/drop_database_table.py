import os
from sqlalchemy import create_engine, text

def drop_table() -> None:
    """
    Drops the 'nps_filings' table in the PostgreSQL database if it exists.
    Uses the connection string from the 'POSTGRES_ENGINE' environment variable.
    """
    if 'POSTGRES_ENGINE' not in os.environ:
        # Fallback for local testing if the environment variable is not set
        os.environ['POSTGRES_ENGINE'] = 'postgres:postgres@localhost:5432/nps_db'

    engine = create_engine(f"postgresql+psycopg2://{os.environ['POSTGRES_ENGINE']}")
    table_name = "nps_filings"

    print(f"Attempting to drop table '{table_name}'...")
    
    with engine.connect() as conn:
        conn.execute(text(f'DROP TABLE IF EXISTS "{table_name}"'))
        conn.commit()
        
    print(f"Table '{table_name}' dropped successfully.")

if __name__ == "__main__":
    drop_table()
