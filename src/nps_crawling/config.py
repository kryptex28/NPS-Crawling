"""Configuration module for NPS Crawling project."""

import copy
import os
import subprocess
from pathlib import Path

from dotenv import load_dotenv

from nps_crawling.project_config import (
    apply_project_data,
    load_project_file,
)

load_dotenv()


def get_git_root() -> Path:
    """Return the root directory of the current Git repository."""
    try:
        return Path(
            subprocess.check_output(
                ["git", "rev-parse", "--show-toplevel"],
                text=True,
            ).strip(),
        )
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        raise RuntimeError(
            "Git-Root konnte nicht ermittelt werden. "
            "Stelle sicher, dass Git installiert ist und das Projekt "
            "innerhalb eines Git-Repositories liegt.",
        ) from exc


class Config:
    """Runtime configuration for crawl, preprocess, and classification pipelines."""

    ROOT_DIR = get_git_root()
    DATA_PATH = ROOT_DIR / "data"

    # ---------------------------------------------------------------------------
    # Local Mode (env-only; not part of project JSON)
    # ---------------------------------------------------------------------------
    LOCAL_MODE: bool = os.getenv("LOCAL_MODE", "0") == "0"
    LOCAL_DB_CONNECTION: str = "crawler:crawler@localhost:5432/crawler"

    # ---------------------------------------------------------------------------
    # Infrastructure paths (not project-specific)
    # ---------------------------------------------------------------------------
    CLASSIFICATION_CACHE_DIR = ROOT_DIR / "src" / "nps_crawling" / "classification" / "cache"
    CLASSIFICATION_CONFIG_DIR = ROOT_DIR / "src" / "nps_crawling" / "classification" / "configurations"

    # ---------------------------------------------------------------------------
    # Active project metadata (set by reload_config)
    # ---------------------------------------------------------------------------
    ACTIVE_PROJECT: str | None = None
    ACTIVE_PROJECT_DESCRIPTION: str | None = None
    DATABASE_TABLE_NAME: str = "default"

    # Crawl
    QUERY_PATH: Path = ROOT_DIR / "query"
    CRAWL_SEC_QUERY_LIMIT_COUNT: int = 10_000
    CRAWL_DOWNLOAD_DELAY: float = 0.2

    # Preprocess
    PREPROCESSING_VERSION: str = "version_2"
    PREPROCESS_FILES_PER_CHUNK: int = 1000
    SINGLE_KEYWORD_FILTER: str | list[str] | None = None
    SINGLE_KEYWORD_FILTER_STRICT: bool = True
    THRESHOLD_KEYWORD_SCOPE: list[str] | None = ["nps"]
    THRESHOLD_KEYWORD_SCOPE_STRICT: bool = True
    SIMILARITY_THRESHOLD_CONTEXT_WINDOW: float = 0.8
    LIST_OF_PHRASES_TO_FILTER_FILINGS_FOR: list = []
    LIST_OF_PHRASES_TO_EXCLUDE: list = []
    SIMILARITY_REFERENCE_TEXT: str = ""
    SIMILARITY_EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    AMOUNT_SENTENCES_INCLUDED_BEFORE: int = 2
    AMOUNT_SENTENCES_INCLUDED_AFTER: int = 2
    MAX_CONTEXT_CHARS_BEFORE_KEYWORD: int = 600
    MAX_CONTEXT_CHARS_AFTER_KEYWORD: int = 600

    # Classification
    CLASSIFICATION_VERSION: str = "version_1"
    CLASSIFICATION_CONFIGURATION: list[dict] = []
    CLASSIFICATION_CONFIG: dict[str, str] = {}
    PROJECT_CATEGORIES: list[dict] = []
    CLASSIFICATION_RANDOM_SEED: int = 42
    CLASSIFICATION_GROUND_TRUTH_TEST_SIZE: float = 0.5
    CLASSIFICATION_FEW_SHOT_NUM_EXAMPLES: int | None = 8
    CLASSIFICATION_FEW_SHOT_TEXT_COLUMN: str = "snippet_text_short"
    CLASSIFICATION_FEW_SHOT_SAMPLE_SEED: int = 43
    CLASSIFICATION_EMBEDDING_BATCH_SIZE: int = 32
    CLASSIFICATION_LLM_BATCH_SIZE: int = 8
    CLASSIFICATION_CONFIG_USE_NAME_FILES: bool = os.getenv(
        "CLASSIFICATION_CONFIG_USE_NAME_FILES", "0"
    ) == "1"

    # Derived data paths (updated by reload_config)
    RAW_JSON_PATH_CRAWLER: Path = DATA_PATH / "default" / "json_raw"
    PROCESSED_BASE_PATH: Path = DATA_PATH / "default" / "json_processed"
    REJECTED_BASE_PATH: Path = DATA_PATH / "default" / "json_rejected"
    CLASSIFIED_BASE_PATH: Path = DATA_PATH / "default" / "json_classified"
    NPS_CONTEXT_JSON_PATH: Path = PROCESSED_BASE_PATH / PREPROCESSING_VERSION
    NPS_REJECTED_JSON_PATH: Path = REJECTED_BASE_PATH / PREPROCESSING_VERSION
    NPS_CLASSIFIED_JSON: Path = CLASSIFIED_BASE_PATH / CLASSIFICATION_VERSION

    @classmethod
    def project_file(cls, project_name: str | None = None) -> Path:
        """Return the JSON path for ``project_name`` or the active project."""
        name = project_name or cls.ACTIVE_PROJECT
        if not name:
            raise ValueError("No active project is loaded.")
        return cls.ROOT_DIR / "projects" / f"{name}.json"

    @classmethod
    def _update_project_paths(cls, root_dir: Path | None = None) -> None:
        root_dir = root_dir or cls.ROOT_DIR
        project_subdir = cls.ACTIVE_PROJECT if cls.ACTIVE_PROJECT else "default"
        cls.RAW_JSON_PATH_CRAWLER = cls.DATA_PATH / project_subdir / "json_raw"
        cls.PROCESSED_BASE_PATH = cls.DATA_PATH / project_subdir / "json_processed"
        cls.REJECTED_BASE_PATH = cls.DATA_PATH / project_subdir / "json_rejected"
        cls.CLASSIFIED_BASE_PATH = cls.DATA_PATH / project_subdir / "json_classified"
        cls.NPS_CONTEXT_JSON_PATH = cls.PROCESSED_BASE_PATH / cls.PREPROCESSING_VERSION
        cls.NPS_REJECTED_JSON_PATH = cls.REJECTED_BASE_PATH / cls.PREPROCESSING_VERSION
        cls.NPS_CLASSIFIED_JSON = cls.CLASSIFIED_BASE_PATH / cls.CLASSIFICATION_VERSION

    @classmethod
    def _ensure_project_directories(cls) -> None:
        if not cls.ACTIVE_PROJECT:
            return
        cls.DATA_PATH.mkdir(parents=True, exist_ok=True)
        project_root = cls.DATA_PATH / cls.ACTIVE_PROJECT
        project_root.mkdir(parents=True, exist_ok=True)
        cls.RAW_JSON_PATH_CRAWLER.mkdir(parents=True, exist_ok=True)
        (cls.RAW_JSON_PATH_CRAWLER / "files").mkdir(parents=True, exist_ok=True)
        (cls.RAW_JSON_PATH_CRAWLER / "crawl_reports").mkdir(parents=True, exist_ok=True)
        cls.PROCESSED_BASE_PATH.mkdir(parents=True, exist_ok=True)
        cls.REJECTED_BASE_PATH.mkdir(parents=True, exist_ok=True)
        cls.CLASSIFIED_BASE_PATH.mkdir(parents=True, exist_ok=True)

    @classmethod
    def apply_defaults(cls) -> None:
        """Reset runtime settings to packaged defaults (no active project)."""
        from nps_crawling.project_config import (
            DEFAULT_CLASSIFICATION_CONFIG,
            DEFAULT_CRAWL_CONFIG,
            DEFAULT_PREPROCESS_CONFIG,
            apply_project_data,
        )

        apply_project_data(
            cls,
            {
                "name": "default",
                "description": "",
                "crawl": copy.deepcopy(DEFAULT_CRAWL_CONFIG),
                "preprocess": copy.deepcopy(DEFAULT_PREPROCESS_CONFIG),
                "classification": copy.deepcopy(DEFAULT_CLASSIFICATION_CONFIG),
            },
            cls.ROOT_DIR,
        )
        cls.ACTIVE_PROJECT = None
        cls.ACTIVE_PROJECT_DESCRIPTION = None
        cls.DATABASE_TABLE_NAME = "default"
        cls._update_project_paths()

    @classmethod
    def apply_project_file(cls, project_file: Path) -> None:
        """Load settings from a project JSON file."""
        project_data = load_project_file(project_file, root_dir=cls.ROOT_DIR)
        apply_project_data(cls, project_data, cls.ROOT_DIR)

    @classmethod
    def reload_config(cls) -> None:
        """Reload configuration from the active project file, if any."""
        from nps_crawling.utils.project_manager import get_active_project_name

        project_name = get_active_project_name()
        if not project_name:
            cls.apply_defaults()
            return

        project_file = cls.ROOT_DIR / "projects" / f"{project_name}.json"
        if not project_file.is_file():
            cls.ACTIVE_PROJECT = project_name
            cls.ACTIVE_PROJECT_DESCRIPTION = ""
            cls.DATABASE_TABLE_NAME = f"{project_name}_db"
            cls._update_project_paths()
            return

        cls.apply_project_file(project_file)

    @classmethod
    def get_classification_configuration_mapping(cls) -> dict[str | dict, str | dict]:
        """Category → model mapping for :class:`ClassificationModelPipeline`."""
        from nps_crawling.project_config import classification_configuration_mapping

        return classification_configuration_mapping(
            {"classification_configuration": cls.CLASSIFICATION_CONFIGURATION},
        )

    @classmethod
    def get_classification_columns_sql(cls) -> str:
        """Returns dynamically generated SQL column definitions for categories."""
        type_mapping = {
            "boolean": "BOOLEAN",
            "float": "DOUBLE PRECISION",
            "int": "INTEGER",
            "integer": "INTEGER",
        }
        category_columns = []
        for cat in cls.PROJECT_CATEGORIES:
            col_name = cat["name"]
            col_type = type_mapping.get(cat["type"].lower(), "BOOLEAN")
            category_columns.append(f'"{col_name}" {col_type}')
        return ",\n        ".join(category_columns)


Config.reload_config()
