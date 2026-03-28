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

    from nps_crawling.config import Config
    json_dir = Config.RAW_JSON_PATH_CRAWLER / "files"

    if not json_dir.exists():
        print(f"Directory {json_dir} does not exist. Please check the path.")
        return

    # Process all JSON files
    added_count = 0
    skipped_count = 0
    files_processed = 0
    keywords_processed = set()

    for json_file in json_dir.glob("*.json"):
        files_processed += 1
        print(f"Processing {json_file.name}...")

        try:
            with open(json_file, "r", encoding="utf-8") as f:
                records = json.load(f)

                for record in records:
                    metadata = record.get("metadata", {})

                    filing = metadata.get("filing", {})
                    keyword = metadata.get("keyword")
                    url = record.get("url")

                    if keyword:
                        keywords_processed.add(keyword)

                    filing_id = filing.get("id")
                    if not filing_id:
                        print("Skipping record with no id")
                        continue

                    if db.filing_exists(filing_id):
                        if keyword:
                            db.add_keyword(filing_id, keyword)
                        skipped_count += 1
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
                        nps_relevant=None,  # Now defaults to None initially
                        path_to_raw=str(json_file.absolute()),
                        url=url,

                        # Main Categories
                        KPI_CURRENT_VALUE=None,
                        KPI_TREND=None,
                        KPI_HISTORICAL_COMPARISON=None,
                        BENCHMARK_COMPARISON=None,
                        TARGET_OUTLOOK=None,
                        MGMT_COMPENSATION_GOVERNANCE=None,
                        CUSTOMER_CASE_EVIDENCE=None,
                        NPS_SERVICE_PROVIDER=None,
                        METHODOLOGY_DEFINITION=None,
                        QUALITATIVE_ONLY=None,
                        OTHER=None,
                        # Category Helper Columns
                        has_numeric_nps=None,
                        numeric_nps_count=None,
                        nps_value_fix=None,
                        nps_competition_industry=None,
                        nps_value_over=None,
                        nps_value_below=None,
                        nps_goal_value=None,
                        nps_goal_change=None,
                        nps_goal_reached=None,
                        nps_trend_detected=None,
                        has_target_language=None,
                        keywords_found=None,
                        matched_phrase=None,
                    )
                    added_count += 1

        except Exception as e:
            print(f"Error processing {json_file.name}: {e}")

    print("\n--- Ingestion Summary ---")
    print(f"Newly added filings: {added_count}")
    print(f"Already existing (skipped/updated): {skipped_count}")
    print(f"Total processed: {added_count + skipped_count}")


if __name__ == "__main__":
    main()
