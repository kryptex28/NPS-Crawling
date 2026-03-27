import os
import sys
from pathlib import Path

from nps_crawling.db.db_adapter import DbAdapter

# Ensure the src directory is in the Python path so module imports work
src_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(src_dir))

if 'POSTGRES_ENGINE' not in os.environ:
    os.environ['POSTGRES_ENGINE'] = 'postgres:postgres@localhost:5432/nps_db'


def test_scenarios() -> None:
    """
    Runs tests to verify specific database scenarios, including checking the idempotency
    of inserting existing filings and ensuring only keywords get added for existing rows,
    as well as verifying the behavior of DOUBLE PRECISION fields.
    """
    print(f"Connecting to database using: {os.environ['POSTGRES_ENGINE']}")
    try:
        adapter = DbAdapter()
    except Exception as e:
        print(f"Failed to connect to DB: {e}")
        return

    test_id = "test_scenario_123"
    print(f"\n--- Testing Database Scenarios for ID: '{test_id}' ---")

    # Clean up before test to ensure a clean slate
    adapter._db.delete_filing(test_id)
    print("Cleaned up existing test data (if any).")

    # --- SCENARIO 1: Insert new filing with DOUBLE PRECISION metrics ---
    print("\n--- Scenario 1: Initial Insert ---")
    keyword_1 = "Initial Keyword"

    # Simulating what happens when a raw JSON is inserted and it DOES NOT exist
    if not adapter.filing_exists(test_id):
        print("Filing does not exist. Inserting new filing...")
        adapter.add_filing(
            filing_id=test_id,
            form="10-K",
            nps_relevant=True,
            display_names=["Scenario Test Inc."],
            # Testing the newly changed DOUBLE PRECISION fields
            nps_value_over=8.5,
            nps_value_below=2.1,
            nps_goal_value=9.0,
        )
        adapter.add_keyword(test_id, keyword_1)
        print("Filing inserted and initial keyword added.")
    else:
        print("Error: Filing should not exist yet!")

    # Verify insertion
    current_val_over = adapter.get_filing_field(test_id, "nps_value_over")
    print(f"Verification - nps_value_over: {current_val_over} (Type: {type(current_val_over)})")

    # --- SCENARIO 2: Attempting to insert the SAME filing again (Pipeline Logic) ---
    print("\n--- Scenario 2: Handing Duplicate Insertion ---")
    keyword_2 = "Second Keyword"

    # Simulating what the pipeline / insert_raw_json does now for duplicates
    if adapter.filing_exists(test_id):
        print("Filing already exists. Skipping full insert and ONLY adding the new keyword.")
        adapter.add_keyword(test_id, keyword_2)
    else:
        print("Error: Filing should exist at this point!")

    # Verify keyword was added and original data wasn't overwritten
    filing = adapter.get_filing(test_id)
    print("Verification - Keywords:", filing.get("keywords"))
    print("Verification - Form string retained:", filing.get("form"))

    # --- SCENARIO 3: Testing get_filing_field for UPPERCASE columns ---
    print("\n--- Scenario 3: Fetching UPPERCASE fields ---")

    # Default should be None since we didn't set it (and changed default to None)
    kpi_val = adapter.get_filing_field(test_id, "KPI_CURRENT_VALUE")
    print(f"Verification - KPI_CURRENT_VALUE: {kpi_val}")

    # Update it to True
    print("Updating KPI_CURRENT_VALUE to True...")
    adapter.update_filing(test_id, KPI_CURRENT_VALUE=True)

    # Fetch again
    kpi_val_new = adapter.get_filing_field(test_id, "KPI_CURRENT_VALUE")
    print(f"Verification - KPI_CURRENT_VALUE (After Update): {kpi_val_new}")

    print("\n--- All Scenarios Completed ---")

    # Optional cleanup:
    adapter._db.delete_filing(test_id)
    print(f"Cleaned up test data for '{test_id}'.")


if __name__ == "__main__":
    test_scenarios()
