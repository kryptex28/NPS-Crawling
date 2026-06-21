import os
import pytest
from sqlalchemy import create_engine
from nps_crawling.config import Config
from nps_crawling.db.db_adapter import DbAdapter

def is_db_available() -> bool:
    """Helper to check if the database is available for the test."""
    try:
        connection_string = os.environ.get('POSTGRES_ENGINE')
        if not connection_string:
            if Config.LOCAL_MODE:
                connection_string = Config.LOCAL_DB_CONNECTION
            else:
                return False
        
        # Test connection
        engine = create_engine(f"postgresql+psycopg2://{connection_string}")
        with engine.connect() as conn:
            return True
    except Exception:
        return False

@pytest.mark.skipif(not is_db_available(), reason="Database connection is not available")
def test_classification_dynamic_schema_and_upsert(monkeypatch):
    """
    Tests dynamic database schema generation, classification upsert,
    and classification retrieval using mocked project/properties.
    """
    # 1. Mock active project so it writes to a test-specific table
    monkeypatch.setattr(Config, "ACTIVE_PROJECT", "test_mock_project")
    monkeypatch.setattr(Config, "DATABASE_TABLE_NAME", "test_mock_project_db")
    from nps_crawling.db.nps_filings_db import NpsFilingsDB
    monkeypatch.setattr(NpsFilingsDB, "TABLE", "test_mock_project_db")
    
    # 2. Define theoretical properties and types for the classifications table (loaded from actual example)
    mock_properties = {
        "KPI_CURRENT_VALUE": "boolean",
        "KPI_TREND": "boolean",
        "KPI_HISTORICAL_COMPARISON": "boolean",
        "TARGET_OUTLOOK": "boolean",
        "NPS_GOAL_REACHED": "boolean",
        "METHODOLOGY_DEFINITION": "boolean",
        "QUALITATIVE_ONLY": "boolean",
        "has_numeric_nps": "boolean",
        "nps_value_fix": "float",
        "nps_competition_industry": "float",
        "nps_value_over": "float",
        "nps_value_below": "float",
        "nps_goal_value": "float",
        "nps_goal_change": "float",
    }
    
    # Mock PROJECT_CATEGORIES in Config to be these exact hardcoded properties
    mock_project_categories = [{"name": k, "type": v} for k, v in mock_properties.items()]
    monkeypatch.setattr(Config, "PROJECT_CATEGORIES", mock_project_categories)
    
    # Assert that all 14 expected categories/properties are loaded in Config.PROJECT_CATEGORIES
    expected_categories = mock_properties
    
    assert len(Config.PROJECT_CATEGORIES) == len(expected_categories), (
        f"Expected {len(expected_categories)} categories in Config.PROJECT_CATEGORIES, "
        f"but got {len(Config.PROJECT_CATEGORIES)}"
    )
    for cat in Config.PROJECT_CATEGORIES:
        name = cat["name"]
        expected_type = expected_categories.get(name)
        assert expected_type is not None, f"Unexpected category {name} found in Config.PROJECT_CATEGORIES"
        assert cat["type"] == expected_type, f"Category {name} expected type {expected_type}, got {cat['type']}"
    
    adapter = DbAdapter()
    
    # 3. Ensure table exists with our custom mock properties
    adapter.ensure_table_exists(
        include_classifications=True,
        classification_properties=mock_properties
    )
    
    # Assert database columns in the created classifications table match the 14 properties
    from sqlalchemy import text
    with adapter.engine.connect() as conn:
        columns_query = text(
            "SELECT column_name, data_type FROM information_schema.columns "
            "WHERE table_name = :table_name"
        )
        rows = conn.execute(columns_query, {"table_name": f"{NpsFilingsDB.TABLE}_classifications".lower()}).mappings().all()
        db_columns = {row["column_name"]: row["data_type"] for row in rows}

    expected_db_types = {
        "KPI_CURRENT_VALUE": "boolean",
        "KPI_TREND": "boolean",
        "KPI_HISTORICAL_COMPARISON": "boolean",
        "TARGET_OUTLOOK": "boolean",
        "NPS_GOAL_REACHED": "boolean",
        "METHODOLOGY_DEFINITION": "boolean",
        "QUALITATIVE_ONLY": "boolean",
        "has_numeric_nps": "boolean",
        "nps_value_fix": "double precision",
        "nps_competition_industry": "double precision",
        "nps_value_over": "double precision",
        "nps_value_below": "double precision",
        "nps_goal_value": "double precision",
        "nps_goal_change": "double precision",
    }

    for col_name, expected_type in expected_db_types.items():
        db_col_key = col_name if col_name in db_columns else col_name.lower()
        assert db_col_key in db_columns, f"Column {col_name} not found in database columns: {list(db_columns.keys())}"
        assert db_columns[db_col_key].lower() == expected_type, f"Column {col_name} has DB type {db_columns[db_col_key]}, expected {expected_type}"

    filing_id = "test_mock_filing_999"
    version = "test_mock_version_123"
    
    try:
        # 4. Insert dummy filing in the main table (required due to Foreign Key reference)
        adapter.add_filing(filing_id=filing_id, form="10-Q", display_names=["Mock Entity"])
        
        # 5. Perform the upsert with all 14 properties
        upsert_data = {
            "KPI_CURRENT_VALUE": True,
            "KPI_TREND": True,
            "KPI_HISTORICAL_COMPARISON": False,
            "TARGET_OUTLOOK": True,
            "NPS_GOAL_REACHED": False,
            "METHODOLOGY_DEFINITION": False,
            "QUALITATIVE_ONLY": False,
            "has_numeric_nps": True,
            "nps_value_fix": 72.5,
            "nps_competition_industry": 65.0,
            "nps_value_over": 70.0,
            "nps_value_below": 50.0,
            "nps_goal_value": 85.0,
            "nps_goal_change": 5.0
        }
        adapter.upsert_classification(
            filing_id=filing_id,
            version=version,
            path_to_classified="/dummy/path.json",
            allowed_cols=set(mock_properties.keys()),
            **upsert_data
        )
        
        # 6. Retrieve classifications using get_classifications method
        classifications = adapter.get_classifications(filing_id)
        
        # 7. Asserts to verify correct insertion and retrieval of all properties
        assert len(classifications) == 1
        retrieved = classifications[0]
        assert retrieved["filing_id"] == filing_id
        assert retrieved["experiment_version"] == version
        
        for key, expected_value in upsert_data.items():
            assert retrieved[key] == expected_value, f"Mismatch for {key}: expected {expected_value}, got {retrieved[key]}"
        
    finally:
        # Cleanup: delete the filing (which also cascade-deletes the classification row)
        try:
            adapter._db.delete_filing(filing_id)
        except Exception:
            pass

if __name__ == "__main__":
    class MonkeyPatchMock:
        def setattr(self, obj, name, value):
            setattr(obj, name, value)
    
    mp = MonkeyPatchMock()
    if is_db_available():
        test_classification_dynamic_schema_and_upsert(mp)
        print("Test passed successfully!")
    else:
        print("Database not available - test skipped.")
