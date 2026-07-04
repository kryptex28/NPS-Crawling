import os
import csv
import pytest
from pathlib import Path
from sqlalchemy import create_engine, text
from nps_crawling.config import Config
from nps_crawling.db.db_adapter import DbAdapter
from nps_crawling.utils import project_manager

def is_db_available() -> bool:
    """Helper to check if the database is available for the test."""
    try:
        return DbAdapter().is_db_available()
    except Exception:
        return False

@pytest.mark.skipif(not is_db_available(), reason="Database connection is not available")
def test_db_export_csv(monkeypatch):
    # 1. Mock active project/table
    monkeypatch.setattr(Config, "ACTIVE_PROJECT", "test_export_proj")
    monkeypatch.setattr(Config, "DATABASE_TABLE_NAME", "test_export_proj_db")
    from nps_crawling.db.nps_filings_db import NpsFilingsDB
    monkeypatch.setattr(NpsFilingsDB, "TABLE", "test_export_proj_db")
    
    # Mock active project name in project_manager to match our test project name
    monkeypatch.setattr(project_manager, "get_active_project_name", lambda: "test_export_proj")
    
    # 2. Define custom category properties
    mock_properties = {
        "KPI_CURRENT_VALUE": "boolean",
        "nps_value_fix": "float",
    }
    mock_project_categories = [{"name": k, "type": v} for k, v in mock_properties.items()]
    monkeypatch.setattr(Config, "PROJECT_CATEGORIES", mock_project_categories)
    monkeypatch.setattr(Config, "CLASSIFICATION_VERSION", "test_class_v1")
    
    adapter = DbAdapter()
    
    # Ensure table exists
    adapter.ensure_table_exists(
        include_classifications=True,
        classification_properties=mock_properties
    )
    
    # Clean up test table if anything exists from a previous aborted run
    with adapter.engine.begin() as conn:
        conn.execute(text(f"DELETE FROM {adapter.table_name}"))
        
    try:
        # Insert three filings:
        # Filing A: project_relevant=True, single ticker "abc"
        # Filing B: project_relevant=True, multiple tickers ["cde", "efg"]
        # Filing C: project_relevant=False, single ticker "xyz"
        adapter.add_filing(
            filing_id="filing_a",
            form="10-K",
            ciks=["0000000001"],
            ticker=["abc"],
            project_relevant=True,
            display_names=["Company A"]
        )
        adapter.add_filing(
            filing_id="filing_b",
            form="10-K",
            ciks=["0000000002"],
            ticker=["cde", "efg"],
            project_relevant=True,
            display_names=["Company B"]
        )
        adapter.add_filing(
            filing_id="filing_c",
            form="10-Q",
            ciks=["0000000003"],
            ticker=["xyz"],
            project_relevant=False,
            display_names=["Company C"]
        )
        
        # Upsert classification results for filing_a
        adapter.upsert_classification(
            filing_id="filing_a",
            version="test_class_v1",
            path_to_classified="/dummy/class_a.json",
            allowed_cols=set(mock_properties.keys()),
            KPI_CURRENT_VALUE=True,
            nps_value_fix=68.5
        )
        
        # Test case 1: Export only_relevant = True
        export_path_str = adapter.export_csv(filename="test_relevant_export.csv", only_relevant=True)
        export_path = Path(export_path_str)
        
        assert export_path.exists()
        assert export_path.name == "test_relevant_export.csv"
        
        # Read export CSV
        with open(export_path, mode="r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            
        # Filing C is not relevant, so it shouldn't be here.
        # Filing A has 1 ticker -> 1 row.
        # Filing B has 2 tickers -> 2 rows.
        # Total rows should be 3.
        assert len(rows) == 3
        
        # Find rows by filing ID
        rows_a = [r for r in rows if r["id"] == "filing_a"]
        rows_b = [r for r in rows if r["id"] == "filing_b"]
        
        assert len(rows_a) == 1
        assert rows_a[0]["ticker"] == "['abc']"
        # Since filing_a has classification results:
        # Check classifications columns
        assert rows_a[0]["KPI_CURRENT_VALUE"] in ("True", "t", "1")
        assert float(rows_a[0]["nps_value_fix"]) == 68.5
        
        assert len(rows_b) == 2
        # Check atomized tickers:
        assert {rows_b[0]["ticker"], rows_b[1]["ticker"]} == {"['cde']", "['efg']"}
        # Filing B was not classified, so classification columns should be empty
        assert rows_b[0]["KPI_CURRENT_VALUE"] in ("", None)
        assert rows_b[0]["nps_value_fix"] in ("", None)
        
        # Test case 2: Export only_relevant = False
        export_all_path_str = adapter.export_csv(filename="test_all_export", only_relevant=False)
        export_all_path = Path(export_all_path_str)
        assert export_all_path.name == "test_all_export.csv"
        
        with open(export_all_path, mode="r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            all_rows = list(reader)
            
        # Filing A (1 ticker) + Filing B (2 tickers) + Filing C (1 ticker) = 4 rows
        assert len(all_rows) == 4
        
    finally:
        # Cleanup
        try:
            adapter._db.delete_filing("filing_a")
            adapter._db.delete_filing("filing_b")
            adapter._db.delete_filing("filing_c")
        except Exception:
            pass

@pytest.mark.skipif(not is_db_available(), reason="Database connection is not available")
def test_export_csv_no_active_project(monkeypatch):
    monkeypatch.setattr(project_manager, "get_active_project_name", lambda: None)
    adapter = DbAdapter()
    with pytest.raises(ValueError, match="Kein aktives Projekt geladen"):
        adapter.export_csv()

@pytest.mark.skipif(not is_db_available(), reason="Database connection is not available")
def test_export_csv_no_classification_table(monkeypatch, capsys):
    # Mock active project/table
    monkeypatch.setattr(Config, "ACTIVE_PROJECT", "test_no_class_proj")
    monkeypatch.setattr(Config, "DATABASE_TABLE_NAME", "test_no_class_proj_db")
    from nps_crawling.db.nps_filings_db import NpsFilingsDB
    monkeypatch.setattr(NpsFilingsDB, "TABLE", "test_no_class_proj_db")
    monkeypatch.setattr(project_manager, "get_active_project_name", lambda: "test_no_class_proj")
    
    adapter = DbAdapter()
    
    # Ensure ONLY the main table exists (include_classifications=False)
    adapter.ensure_table_exists(include_classifications=False)
    
    with adapter.engine.begin() as conn:
        conn.execute(text(f"DELETE FROM {adapter.table_name}"))
        
    try:
        adapter.add_filing(
            filing_id="filing_x",
            form="10-K",
            ticker=["xyz"],
            project_relevant=True
        )
        
        # Capture print statements to check for warning
        export_path_str = adapter.export_csv(filename="test_no_class_export.csv", only_relevant=False)
        export_path = Path(export_path_str)
        
        assert export_path.exists()
        
        # Verify the CSV row has main table properties but no classification properties
        with open(export_path, mode="r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            
        assert len(rows) == 1
        assert rows[0]["id"] == "filing_x"
        assert "KPI_CURRENT_VALUE" not in rows[0]  # Classification col shouldn't be present
        
        # Verify stdout warning message
        captured = capsys.readouterr()
        assert "Die Klassifikationstabelle" in captured.out
        assert "existiert nicht" in captured.out
        
    finally:
        try:
            adapter._db.delete_filing("filing_x")
        except Exception:
            pass

@pytest.mark.skipif(not is_db_available(), reason="Database connection is not available")
def test_export_csv_db_not_available(monkeypatch):
    monkeypatch.setattr(project_manager, "get_active_project_name", lambda: "test_export_proj")
    adapter = DbAdapter()
    monkeypatch.setattr(adapter, "is_db_available", lambda: False)
    with pytest.raises(ConnectionError, match="Datenbank ist nicht erreichbar"):
        adapter.export_csv()

def test_is_db_available_local_mode_docker_retry(monkeypatch):
    # This test verifies the retry/auto-start behavior using mocks and runs in-memory
    monkeypatch.setattr(Config, "LOCAL_MODE", True)
    
    # Create adapter with a dummy engine that we will mock
    adapter = DbAdapter()
    
    call_count = 0
    class MockConnection:
        def __enter__(self):
            return self
        def __exit__(self, exc_type, exc_val, exc_tb):
            pass
        def execute(self, statement, *multiparams, **params):
            pass

    def mock_connect():
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise Exception("DB is offline")
        return MockConnection()
        
    monkeypatch.setattr(adapter.engine, "connect", mock_connect)
    
    docker_called = False
    def mock_ensure_docker_db_running():
        nonlocal docker_called
        docker_called = True
        
    import nps_crawling.db.ensure_docker
    monkeypatch.setattr(nps_crawling.db.ensure_docker, "ensure_docker_db_running", mock_ensure_docker_db_running)
    
    # Check that availability check succeeds on retry and docker was called
    assert adapter.is_db_available() is True
    assert docker_called is True
    assert call_count == 2

