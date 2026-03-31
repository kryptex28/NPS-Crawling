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
            "LOCAL_MODE=False und die Umgebungsvariable POSTGRES_ENGINE ist nicht gesetzt."
        )
    return conn


def create_table() -> None:
    """
    Creates the 'nps_filings' table in the PostgreSQL database if it does not already exist.
    Verbindung wird ueber Config.LOCAL_MODE oder die Umgebungsvariable POSTGRES_ENGINE bestimmt.
    """
    engine = create_engine(f"postgresql+psycopg2://{_get_connection_string()}")

    table_name = Config.DATABASE_TABLE_NAME

    # Drop table if exists for a clean slate, or just create if not exists
    create_stmt = text(f"""
    CREATE TABLE IF NOT EXISTS {table_name} (
        id VARCHAR PRIMARY KEY,

        -- SEC Metadata
        ciks TEXT[],
        period_ending DATE,
        display_names TEXT[],
        root_forms TEXT[],
        file_date DATE,
        form VARCHAR,
        adsh VARCHAR,
        file_type VARCHAR,
        file_description TEXT,
        film_num TEXT[],

        -- Extraction/Processing Metadata
        keywords TEXT[],
        blacklisted BOOLEAN DEFAULT FALSE,
        nps_relevant BOOLEAN,

        -- File Paths
        path_to_raw VARCHAR,
        path_to_preprocessed VARCHAR,
        path_to_classified VARCHAR,
        url VARCHAR,

        -- Main Categories
        "KPI_CURRENT_VALUE" BOOLEAN,
        "KPI_TREND" BOOLEAN,
        "KPI_HISTORICAL_COMPARISON" BOOLEAN,
        "BENCHMARK_COMPARISON" BOOLEAN,
        "TARGET_OUTLOOK" BOOLEAN,
        "MGMT_COMPENSATION_GOVERNANCE" BOOLEAN,
        "CUSTOMER_CASE_EVIDENCE" BOOLEAN,
        "NPS_SERVICE_PROVIDER" BOOLEAN,
        "METHODOLOGY_DEFINITION" BOOLEAN,
        "QUALITATIVE_ONLY" BOOLEAN,
        "OTHER" BOOLEAN,

        -- Category Helper Columns
        has_numeric_nps BOOLEAN,
        numeric_nps_count INTEGER,
        nps_value_fix DOUBLE PRECISION,
        nps_competition_industry BOOLEAN,
        nps_value_over DOUBLE PRECISION,
        nps_value_below DOUBLE PRECISION,
        nps_goal_value DOUBLE PRECISION,
        nps_goal_change DOUBLE PRECISION,
        nps_goal_reached BOOLEAN,
        nps_trend_detected BOOLEAN,
        has_target_language BOOLEAN,
        keywords_found VARCHAR,
        matched_phrase VARCHAR,

        -- Crawl Tracking
        last_crawled TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    );
    """)

    with engine.begin() as conn:
        conn.execute(create_stmt)
        print(f"Table '{table_name}' checked/created successfully.")


if __name__ == "__main__":
    create_table()
