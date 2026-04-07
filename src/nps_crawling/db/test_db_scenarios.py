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
    Runs comprehensive database scenarios covering filing inserts,
    duplicate handling, array modifications (keywords), and the complete cycle
    of the new relational Classification table (multiple versions, updates, cascading deletes).
    """
    print(f"Connecting to database using: {os.environ['POSTGRES_ENGINE']}")
    try:
        adapter = DbAdapter()
    except Exception as e:
        print(f"Failed to connect to DB: {e}")
        return

    test_id = "test_scenario_comprehensive"
    print(f"\n======== Testing Database Scenarios for ID: '{test_id}' ========")

    # Clean up before test to ensure a clean slate
    adapter._db.delete_filing(test_id)
    print("Cleaned up existing test data (if any).")

    # --- SCENARIO 1: Base Filing Insertion & Duplicates ---
    print("\n--- Scenario 1: Base Filing Insert & Keyword Appending ---")
    
    # Simulating what happens when a raw JSON is inserted and it DOES NOT exist
    if not adapter.filing_exists(test_id):
        print("Filing does not exist. Inserting new filing metadata...")
        adapter.add_filing(
            filing_id=test_id,
            form="10-K",
            nps_relevant=True,
            display_names=["Scenario Test Inc."],
        )
        adapter.add_keyword(test_id, "Initial Keyword")
    
    # Simulating what the pipeline / insert_raw_json does now for duplicates
    if adapter.filing_exists(test_id):
        print("Attempting duplicate filing insert. Adding second keyword...")
        adapter.add_keyword(test_id, "Second Keyword")
        
    filing = adapter.get_filing(test_id)
    print(f"Verification - Keywords: {filing.get('keywords')}")
    print(f"Verification - Form string retained: {filing.get('form')}")


    # --- SCENARIO 2: Classification Version 1 (Insert) ---
    print("\n--- Scenario 2: First Classification Run (Version: ollama_v1) ---")
    
    adapter.upsert_classification(
        filing_id=test_id,
        version="ollama_v1",
        BENCHMARK_COMPARISON_POSITIVE=True,
        KPI_CURRENT_VALUE=True,
        has_numeric_nps=True,
        nps_value_over=8.5,
        nps_value_below=2.1,
    )
    print("Upserted classification for 'ollama_v1'")
    
    classifs = adapter.get_classifications(test_id)
    v1_data = next((c for c in classifs if c["experiment_version"] == "ollama_v1"), None)
    print(f"Verification - Total Classifications found: {len(classifs)}")
    print(f"Verification (v1) - BENCHMARK_COMPARISON_POSITIVE: {v1_data.get('BENCHMARK_COMPARISON_POSITIVE')}")
    print(f"Verification (v1) - nps_value_over: {v1_data.get('nps_value_over')}")


    # --- SCENARIO 3: Classification Version 2 (Experiment isolation) ---
    print("\n--- Scenario 3: Second Classification Run (Version: svm_v2) ---")
    
    adapter.upsert_classification(
        filing_id=test_id,
        version="svm_v2",
        BENCHMARK_COMPARISON_POSITIVE=False,  # Model disagreed
        BENCHMARK_COMPARISON_NEGATIVE=True,
        nps_value_over=7.0, # Found a different value
    )
    print("Upserted classification for 'svm_v2'")
    
    classifs_both = adapter.get_classifications(test_id)
    v1_data_again = next((c for c in classifs_both if c["experiment_version"] == "ollama_v1"), None)
    v2_data = next((c for c in classifs_both if c["experiment_version"] == "svm_v2"), None)
    
    print(f"Verification - Total Classifications found: {len(classifs_both)} (Should be 2)")
    print(f"Verification (v1) - nps_value_over: {v1_data_again.get('nps_value_over')} (Should still be 8.5)")
    print(f"Verification (v2) - nps_value_over: {v2_data.get('nps_value_over')} (Should be 7.0)")


    # --- SCENARIO 4: Classification Updates (Idempotency / Re-run) ---
    print("\n--- Scenario 4: Re-running classification (ON CONFLICT UPDATE) ---")
    
    print("Updating 'ollama_v1' to change a field...")
    adapter.upsert_classification(
        filing_id=test_id,
        version="ollama_v1",
        KPI_CURRENT_VALUE=False, # Changed result
        has_numeric_nps=True,
        nps_value_over=8.5, # Remains same
    )
    
    classifs_updated = adapter.get_classifications(test_id)
    v1_data_updated = next((c for c in classifs_updated if c["experiment_version"] == "ollama_v1"), None)
    
    print(f"Verification - Total Classifications found: {len(classifs_updated)} (Should STILL be 2, no new row)")
    print(f"Verification (v1 updated) - KPI_CURRENT_VALUE: {v1_data_updated.get('KPI_CURRENT_VALUE')} (Should be False)")


    # --- SCENARIO 5: Delete Cascade ---
    print("\n--- Scenario 5: Cascading Deletes ---")
    print("Deleting the original Filing metadata row...")
    
    adapter._db.delete_filing(test_id)
    
    filing_check = adapter.get_filing(test_id)
    classifs_check = adapter.get_classifications(test_id)
    
    print(f"Verification - Filing row exists: {filing_check is not None}")
    print(f"Verification - Classification rows remaining: {len(classifs_check)} (Should be 0 due to CASCADE)")

    print("\n======== All Scenarios Completed Successfully ========")


if __name__ == "__main__":
    test_scenarios()
