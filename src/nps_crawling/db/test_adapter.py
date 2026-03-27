import os
import sys
from pathlib import Path

from nps_crawling.db.db_adapter import DbAdapter

# Ensure the src directory is in the Python path so module imports work
src_dir = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(src_dir))

# Set mock environment for the test script (ensure this DB exists in your local postgres!)
# Alternatively, replace this with your actual local test DB credentials.
if 'POSTGRES_ENGINE' not in os.environ:
    os.environ['POSTGRES_ENGINE'] = 'postgres:postgres@localhost:5432/nps_db'


def test_adapter() -> None:
    """
    Runs basic tests to verify that the DbAdapter can insert filings,
    update fields and file paths, and retrieve rows from the database.
    """
    print(f"Connecting to database using: {os.environ['POSTGRES_ENGINE']}")
    try:
        adapter = DbAdapter()
    except Exception as e:
        print(f"Failed to connect to DB: {e}")
        return

    test_id = "test"
    print(f"\n--- Testing DbAdapter with ID: '{test_id}' ---")

    # 1. Add filing (simulate scrapy pipeline)
    print("\n1. Testing add_filing (Upsert)...")
    adapter.add_filing(filing_id=test_id, form="10-K", nps_relevant=True, display_names=["Test Company Inc."])
    print(f"Filing '{test_id}' added/upserted.")

    # 2. Check if filing exists
    print("\n2. Testing filing_exists...")
    exists = adapter.filing_exists(filing_id=test_id)
    print(f"Filing exists: {exists}")

    # 3. Test Path Updates (Simulating the different pipeline stages storing JSONs)
    print("\n3. Testing path update methods...")

    # Raw path (Scrapy storage)
    updated_raw = adapter.update_path_to_raw(filing_id=test_id, path="/fake/path/to/raw.json")
    print(f"update_path_to_raw successful: {updated_raw}")

    # Preprocessed path
    updated_prep = adapter.update_path_to_preprocessed(filing_id=test_id, path="/fake/path/to/preprocessed.json")
    print(f"update_path_to_preprocessed successful: {updated_prep}")

    # Classified path
    updated_class = adapter.update_path_to_classified(filing_id=test_id, path="/fake/path/to/classified.json")
    print(f"update_path_to_classified successful: {updated_class}")

    # 4. Test Single / Multi Field Dynamic Update
    print("\n4. Testing generic update_filing method...")
    updated_fields = adapter.update_filing(
        filing_id=test_id,
        nps_goal_reached=True,
        nps_value_fix=10.5,
        nps_trend_sentiment="Super Positive",
    )
    print(f"update_filing successful: {updated_fields}")

    # 5. Add keyword (Test array appending without overwriting)
    print("\n5. Testing add_keyword...")
    keyword_added_1 = adapter.add_keyword(filing_id=test_id, keyword="NPS")
    print(f"Keyword 'NPS' added: {keyword_added_1}")

    keyword_added_2 = adapter.add_keyword(filing_id=test_id, keyword="Net Promoter Score")
    print(f"Keyword 'Net Promoter Score' added: {keyword_added_2}")

    # Try adding the same keyword again to test idempotency (Should return False/None usually)
    keyword_added_dup = adapter.add_keyword(filing_id=test_id, keyword="NPS")
    print(f"Duplicate Keyword 'NPS' added (Should safely ignore): {keyword_added_dup}")

    # 6. Retrieve and verify the item
    print("\n6. Testing get_filing...")
    item = adapter.get_filing(filing_id=test_id)
    if item:
        print("\nSuccessfully retrieved filing. Here is the current state:")
        for key, value in item.items():
            # Only print fields that have actual values to keep output readable
            if value is not None and value != [] and value:
                print(f"  {key}: {value}")
    else:
        print("Failed to retrieve filing.")


if __name__ == "__main__":
    test_adapter()
