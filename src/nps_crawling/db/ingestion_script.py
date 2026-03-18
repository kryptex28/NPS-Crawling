import json
import os
from pathlib import Path

from nps_crawling.db.db_adapter import DbAdapter


def main() -> None:
    """
    Reads all raw JSON files from the data/json_raw directory and inserts them into the database.
    If a filing already exists, only the new keyword is added to the existing record.
    """
    try:
        db = DbAdapter()
    except Exception as e:
        print(f"Failed to initialize database connection: {e}")
        return

    # Using the current working directory, adjusting for the project folder structure
    # Based on Config.RAW_JSON_PATH_CRAWLER which is data/json_raw
    json_dir = Path.cwd() / "data" / "json_raw"

    if not json_dir.exists():
        print(f"Directory {json_dir} does not exist. Please check the path.")
        return

    # Process all JSON files
    inserted_count = 0
    for json_file in json_dir.glob("*.json"):
        print(f"Processing {json_file.name}...")

        try:
            with open(json_file, "r", encoding="utf-8") as f:
                records = json.load(f)

                for record in records:
                    metadata = record.get("metadata", {})

                    filing = metadata.get("filing", {})
                    keyword = metadata.get("keyword")

                    filing_id = filing.get("id")
                    if not filing_id:
                        print("Skipping record with no id")
                        continue

                    if db.filing_exists(filing_id):
                        if keyword:
                            db.add_keyword(filing_id, keyword)
                        inserted_count += 1
                        continue

                    # Store keywords in an array
                    keywords = [keyword] if keyword else []

                    # Convert date strings to python dates or pass them as strings
                    # SQLAlchemy text statements with PostgreSQL are fine with ISO date strings

                    # Call adapter add_filing with data mapped from the JSON and None/False for new fields automatically
                    db.add_filing(
                        filing_id=filing_id,
                        ciks=filing.get("ciks", []),
                        period_ending=filing.get("period_ending"),
                        display_names=filing.get("display_names", []),
                        root_forms=filing.get("root_forms", []),
                        file_date=filing.get("file_date"),
                        form=filing.get("form"),
                        adsh=filing.get("adsh"),
                        file_type=filing.get("file_type"),
                        file_description=filing.get("file_description"),
                        film_num=filing.get("film_num", []),
                        keywords=keywords,
                        blacklisted=False,
                        nps_relevant=False,  # Now defaults to False initially
                        path_to_raw=str(json_file.absolute()),

                        # New NPS fields set to default values explicitly
                        nps_competition_industry=False,
                        nps_value_over=None,
                        nps_value_below=None,
                        nps_goal_value=None,
                        nps_goal_reached=False,
                        KPI_CURRENT_VALUE=False,
                        KPI_HISTORICAL_COMPARISON=False,
                        BENCHMARK_COMPARISON=False,
                        CUSTOMER_CASE_EVIDENCE=False,
                        METHODOLOGY_DEFINITION=False,
                        MGMT_COMPENSATION_GOVERNANCE=False,
                        QUALITATIVE_ONLY=False,
                        TARGET_OUTLOOK=False,
                        NPS_SERVICE_PROVIDER=False,
                        OTHER=False,
                        has_numeric_nps=False,
                        nps_value_fix=None,
                        nps_trend_sentiment=None,
                        nps_scope=None,
                        nps_formal_role=None,
                    )
                    inserted_count += 1

        except Exception as e:
            print(f"Error processing {json_file.name}: {e}")

    print(f"Total records processed and inserted/updated: {inserted_count}")


if __name__ == "__main__":
    main()
