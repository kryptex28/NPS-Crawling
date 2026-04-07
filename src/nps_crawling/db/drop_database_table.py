import os

from sqlalchemy import create_engine, text

from nps_crawling.config import Config


def _get_connection_string() -> str:
    """Gibt den Verbindungsstring basierend auf Config.LOCAL_MODE zurueck."""
    if Config.LOCAL_MODE:
        return Config.LOCAL_DB_CONNECTION
    conn = os.environ.get('POSTGRES_ENGINE')
    if not conn:
        raise RuntimeError(
            "LOCAL_MODE=False und die Umgebungsvariable POSTGRES_ENGINE ist nicht gesetzt.",
        )
    return conn


def drop_table() -> None:
    """
    Drops the 'nps_filings' table in the PostgreSQL database if it exists.
    Verbindung wird ueber Config.LOCAL_MODE oder die Umgebungsvariable POSTGRES_ENGINE bestimmt.
    """
    engine = create_engine(f"postgresql+psycopg2://{_get_connection_string()}")

    table_name = Config.DATABASE_TABLE_NAME

    print(f"Attempting to drop tables '{table_name}' and '{table_name}_classifications'...")

    with engine.connect() as conn:
        # Drop the classification table first to easily avoid foreign key constraint issues
        conn.execute(text(f'DROP TABLE IF EXISTS "{table_name}_classifications" CASCADE'))
        # Then drop the main table
        conn.execute(text(f'DROP TABLE IF EXISTS "{table_name}" CASCADE'))
        conn.commit()

    print(f"Tables '{table_name}' and '{table_name}_classifications' dropped successfully.")


if __name__ == "__main__":
    drop_table()
