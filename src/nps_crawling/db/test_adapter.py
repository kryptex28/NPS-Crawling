import os
import sys
from pathlib import Path

# Ensure the src directory is in the Python path so module imports work
src_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(src_dir))

# Backup and mock active project for testing using the first available project config file
active_file = src_dir.parent / ".active_project"
temp_backup = src_dir.parent / ".active_project.backup"

if active_file.exists():
    try:
        active_file.rename(temp_backup)
    except Exception:
        pass

# Find first project config to use as mock, fallback to "example_project" if none found
projects_dir = src_dir.parent / "projects"
project_files = list(projects_dir.glob("*.json"))
mock_project = project_files[0].stem if project_files else "example_project"

active_file.write_text(mock_project, encoding="utf-8")

from nps_crawling.db.db_adapter import DbAdapter

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
        adapter.ensure_table_exists()
    except Exception as e:
        print(f"Failed to connect to DB or ensure table exists: {e}")
        sys.exit(1)

    test_id = "test"
    print(f"\n--- Testing DbAdapter with ID: '{test_id}' ---")

    # 1. Add filing (simulate scrapy pipeline)
    print("\n1. Testing add_filing (Upsert)...")
    adapter.add_filing(filing_id=test_id, form="10-K", project_relevant=True, display_names=["Test Company Inc."])
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
        url="https://example.com/test",
    )
    print(f"update_filing successful: {updated_fields}")
    # 4b. Test Classification Upsert (Multiple Versions)
    print("\n4b. Testing upsert_classification method (Multiple Versions)...")
    adapter.upsert_classification(
        filing_id=test_id,
        version="test_version_1",
        NPS_GOAL_REACHED=True,
        nps_value_fix=10.5,
    )
    print("upsert_classification for version 'test_version_1' successful.")

    adapter.upsert_classification(
        filing_id=test_id,
        version="test_version_2",
        NPS_GOAL_REACHED=False,
        nps_value_fix=7.2,
    )
    print("upsert_classification for version 'test_version_2' successful.")

    classifs = adapter.get_classifications(filing_id=test_id)
    print(f"Found classifications (Expected 2 versions): {classifs}")

    # 4c. Test Preprocessing Upsert (Multiple Versions)
    print("\n4c. Testing upsert_preprocessing_result method (Multiple Versions)...")
    adapter.upsert_preprocessing_result(
        filing_id=test_id,
        version="prep_version_1",
        project_relevant=True,
        path_to_preprocessed="/dummy/prep_v1.json"
    )
    print("upsert_preprocessing_result for version 'prep_version_1' successful.")

    adapter.upsert_preprocessing_result(
        filing_id=test_id,
        version="prep_version_2",
        project_relevant=False,
        path_to_preprocessed="/dummy/prep_v2.json"
    )
    print("upsert_preprocessing_result for version 'prep_version_2' successful.")

    # Retrieve preprocessing entries via raw SQL to verify they both exist
    from sqlalchemy import text
    stmt_prep = text(f"SELECT * FROM {adapter.table_name}_preprocessing WHERE filing_id = :id")
    with adapter.engine.connect() as conn:
        prep_rows = conn.execute(stmt_prep, {"id": test_id}).mappings().all()
    print(f"Found preprocessing versions (Expected 2 versions): {[dict(r) for r in prep_rows]}")

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

    # 7. Cleanup test data
    print("\n7. Cleaning up test data...")
    adapter._db.delete_filing(test_id)
    print("Cleanup successful.")


if __name__ == "__main__":
    try:
        test_adapter()
    finally:
        if active_file.exists():
            try:
                active_file.unlink()
            except Exception:
                pass
        if temp_backup.exists():
            try:
                temp_backup.rename(active_file)
            except Exception:
                pass
