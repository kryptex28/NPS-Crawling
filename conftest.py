import json
from pathlib import Path
from nps_crawling.config import Config

# Force Config to use test_project in-memory for the duration of the pytest session
Config.ACTIVE_PROJECT = "test_project"
_project_file = Config.ROOT_DIR / "projects" / "test_project.json"
if _project_file.exists():
    try:
        with open(_project_file, "r", encoding="utf-8") as f:
            Config.ACTIVE_PROJECT_CONFIG = json.load(f)
    except Exception:
        pass

# Force the database table to use test_project_db
Config.DATABASE_TABLE_NAME = "test_project_db"

# Recalculate other paths that depend on ACTIVE_PROJECT
_proj_sub = "test_project"
Config.RAW_JSON_PATH_CRAWLER = Config.DATA_PATH / _proj_sub / "json_raw"
Config.PROCESSED_BASE_PATH = Config.DATA_PATH / _proj_sub / "json_processed"
Config.REJECTED_BASE_PATH = Config.DATA_PATH / _proj_sub / "json_rejected"
Config.CLASSIFIED_BASE_PATH = Config.DATA_PATH / _proj_sub / "json_classified"

Config.NPS_CONTEXT_JSON_PATH = Config.PROCESSED_BASE_PATH / Config.PREPROCESSING_VERSION
Config.NPS_REJECTED_JSON_PATH = Config.REJECTED_BASE_PATH / Config.PREPROCESSING_VERSION
Config.NPS_CLASSIFIED_JSON = Config.CLASSIFIED_BASE_PATH / Config.CLASSIFICATION_VERSION
