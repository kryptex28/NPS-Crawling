import os

from sqlalchemy import create_engine, text


def create_table() -> None:
    """
    Creates the 'nps_filings' table in the PostgreSQL database if it does not already exist.
    Uses the connection string from the 'POSTGRES_ENGINE' environment variable.
    """
    # Connect to PostgreSQL using the environment variable
    engine = create_engine(f"postgresql+psycopg2://{os.environ['POSTGRES_ENGINE']}")

    table_name = "nps_filings"

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
        nps_relevant BOOLEAN DEFAULT FALSE,

        -- File Paths
        path_to_raw VARCHAR,
        path_to_preprocessed VARCHAR,
        path_to_classified VARCHAR,
        url VARCHAR,

        -- New NPS Fields
        nps_competition_industry BOOLEAN,
        nps_value_over DOUBLE PRECISION,
        nps_value_below DOUBLE PRECISION,
        nps_goal_value DOUBLE PRECISION,
        nps_goal_reached BOOLEAN,
        "KPI_CURRENT_VALUE" BOOLEAN,
        "KPI_HISTORICAL_COMPARISON" BOOLEAN,
        "BENCHMARK_COMPARISON" BOOLEAN,
        "CUSTOMER_CASE_EVIDENCE" BOOLEAN,
        "METHODOLOGY_DEFINITION" BOOLEAN,
        "MGMT_COMPENSATION_GOVERNANCE" BOOLEAN,
        "QUALITATIVE_ONLY" BOOLEAN,
        "TARGET_OUTLOOK" BOOLEAN,
        "NPS_SERVICE_PROVIDER" BOOLEAN,
        "OTHER" BOOLEAN,
        has_numeric_nps BOOLEAN DEFAULT FALSE,
        nps_value_fix DOUBLE PRECISION,
        nps_trend_sentiment VARCHAR,
        nps_scope VARCHAR,
        nps_formal_role VARCHAR,

        -- Crawl Tracking
        last_crawled TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    );
    """)

    with engine.begin() as conn:
        conn.execute(create_stmt)
        print(f"Table '{table_name}' checked/created successfully.")


if __name__ == "__main__":
    create_table()
