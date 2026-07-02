"""Configuration module for NPS Crawling project."""

import subprocess
from pathlib import Path
import os
import json
from dotenv import load_dotenv
from enum import Enum

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
    """PATHS."""

    ROOT_DIR = get_git_root()
    DATA_PATH = ROOT_DIR / "data"
    QUERY_PATH = ROOT_DIR / "query"
    GUI_QUERY_PATH = ROOT_DIR / "gui_query"

    # Active Project
    ACTIVE_PROJECT: str | None = None
    ACTIVE_PROJECT_DESCRIPTION: str | None = None
    try:
        from nps_crawling.utils.project_manager import get_active_project
        _project_info = get_active_project()
        if _project_info:
            ACTIVE_PROJECT = _project_info[0]
            ACTIVE_PROJECT_DESCRIPTION = _project_info[1]
    except Exception:
        pass

    @classmethod
    def reload_config(cls) -> None:
        """Reloads the active project from the project manager and recalculates all dependent configurations."""
        from nps_crawling.utils.project_manager import get_active_project
        _project_info = get_active_project()
        if _project_info:
            cls.ACTIVE_PROJECT = _project_info[0]
            cls.ACTIVE_PROJECT_DESCRIPTION = _project_info[1]
        else:
            cls.ACTIVE_PROJECT = None
            cls.ACTIVE_PROJECT_DESCRIPTION = None

        cls.DATABASE_TABLE_NAME = (
            f"{cls.ACTIVE_PROJECT}_db" if cls.ACTIVE_PROJECT else "default"
        )

        _proj_sub = cls.ACTIVE_PROJECT if cls.ACTIVE_PROJECT else "default"
        cls.RAW_JSON_PATH_CRAWLER = cls.DATA_PATH / _proj_sub / "json_raw"
        cls.PROCESSED_BASE_PATH = cls.DATA_PATH / _proj_sub / "json_processed"
        cls.REJECTED_BASE_PATH = cls.DATA_PATH / _proj_sub / "json_rejected"
        cls.CLASSIFIED_BASE_PATH = cls.DATA_PATH / _proj_sub / "json_classified"

        cls.NPS_CONTEXT_JSON_PATH = cls.PROCESSED_BASE_PATH / cls.PREPROCESSING_VERSION
        cls.NPS_REJECTED_JSON_PATH = cls.REJECTED_BASE_PATH / cls.PREPROCESSING_VERSION
        cls.NPS_CLASSIFIED_JSON = cls.CLASSIFIED_BASE_PATH / cls.CLASSIFICATION_VERSION

    @classmethod
    def get_classification_columns_sql(cls) -> str:
        """Returns dynamically generated SQL column definitions for categories."""
        type_mapping = {
            "boolean": "BOOLEAN",
            "float": "DOUBLE PRECISION",
            "int": "INTEGER",
            "integer": "INTEGER"
        }
        category_columns = []
        for cat in cls.PROJECT_CATEGORIES:
            col_name = cat["name"]
            col_type = type_mapping.get(cat["type"].lower(), "BOOLEAN")
            category_columns.append(f'"{col_name}" {col_type}')
        return ",\n        ".join(category_columns)

    # ---------------------------------------------------------------------------
    # Local Mode
    # ---------------------------------------------------------------------------
    # Wenn True: Die Docker-Postgres (docker/database/docker-compose.yml) wird
    # beim Programmstart automatisch hochgefahren und als Datenbank verwendet.
    # Wenn False: Die Umgebungsvariable POSTGRES_ENGINE muss gesetzt sein.

    # .env LOCAL_MODE=1 to enable local mode, .env LOCAL_MODE=0 to disable local mode
    # defaults to False if not set to not interfere with existing server setup
    LOCAL_MODE: bool = os.getenv("LOCAL_MODE", "0") == "0"

    # Verbindungsstring für die lokale Docker-Postgres (user:password@host:port/db)
    LOCAL_DB_CONNECTION: str = "crawler:crawler@localhost:5432/crawler"
    # ---------------------------------------------------------------------------

    # Database Settings
    DATABASE_TABLE_NAME: str = (
        f"{ACTIVE_PROJECT}_db" if ACTIVE_PROJECT else "default"
    )

    # Define experiment name, preprocessing version and classification version.
    # For PREPROCESSING:
    # Will check if data/json_processed/<PREPROCESSING_VERSION> already exists.
    # If so, preprocessing will be skipped entirely.
    # If not, it will create it and save the preprocessed JSONs there with the
    # configurations set below.
    PREPROCESSING_VERSION: str = "version_2"
    CLASSIFICATION_VERSION: str = "version_1"

    # Base directories
    _proj_sub = ACTIVE_PROJECT if ACTIVE_PROJECT else "default"
    RAW_JSON_PATH_CRAWLER = DATA_PATH / _proj_sub / "json_raw"
    PROCESSED_BASE_PATH = DATA_PATH / _proj_sub / "json_processed"
    REJECTED_BASE_PATH = DATA_PATH / _proj_sub / "json_rejected"
    CLASSIFIED_BASE_PATH = DATA_PATH / _proj_sub / "json_classified"

    # Experiment-specific directories
    NPS_CONTEXT_JSON_PATH = PROCESSED_BASE_PATH / PREPROCESSING_VERSION
    NPS_REJECTED_JSON_PATH = REJECTED_BASE_PATH / PREPROCESSING_VERSION
    NPS_CLASSIFIED_JSON = CLASSIFIED_BASE_PATH / CLASSIFICATION_VERSION

    # Create base directories (only if a project is loaded)
    if ACTIVE_PROJECT:
        DATA_PATH.mkdir(parents=True, exist_ok=True)
        (DATA_PATH / _proj_sub).mkdir(parents=True, exist_ok=True)
        RAW_JSON_PATH_CRAWLER.mkdir(parents=True, exist_ok=True)
        (RAW_JSON_PATH_CRAWLER / "files").mkdir(parents=True, exist_ok=True)
        (RAW_JSON_PATH_CRAWLER / "crawl_reports").mkdir(parents=True, exist_ok=True)
        PROCESSED_BASE_PATH.mkdir(parents=True, exist_ok=True)
        REJECTED_BASE_PATH.mkdir(parents=True, exist_ok=True)
        CLASSIFIED_BASE_PATH.mkdir(parents=True, exist_ok=True)
    # Note: Version-specific dirs (NPS_CONTEXT_JSON_PATH, NPS_REJECTED_JSON_PATH,
    # NPS_CLASSIFIED_JSON) are created lazily by the respective pipeline constructors.

    """ PREPROCESSING CONFIG """
    # When set, only filings whose db keywords list matches the keywords in this list are preprocessed.
    # Set to None to disable this filter and process all filings.
    # It can be a single string (exact match) or a list of strings (any match).
    SINGLE_KEYWORD_FILTER: str | list[str] | None = None
    # If STRICT is True, filings are only included if they contain EXACTLY ONE keyword and it matches.
    # If STRICT is False, filings are included if they contain at least one of the keywords (even if they have others).
    SINGLE_KEYWORD_FILTER_STRICT: bool = True

    # Controls which filings have SIMILARITY_THRESHOLD_CONTEXT_WINDOW applied.
    # Set to None to apply the threshold to every processed filing.
    # When set, the threshold is applied only to filings whose DB keyword set matches this scope;
    # filings outside the scope auto-accept all context windows (similarity scores are still
    # computed and saved).
    THRESHOLD_KEYWORD_SCOPE: list[str] | None = ["nps"]
    # If STRICT is True, the threshold is applied only when the filing's DB keyword set is
    # EXACTLY equal to THRESHOLD_KEYWORD_SCOPE (e.g. filing has only "nps" and nothing else).
    # If STRICT is False, the threshold is applied whenever the filing's DB keywords intersect
    # THRESHOLD_KEYWORD_SCOPE (e.g. filing has "nps" alongside other keywords).
    THRESHOLD_KEYWORD_SCOPE_STRICT: bool = True

    # Define Threshold for similarity search here. Context windows that fall below
    # this value will be filtered out. This means the higher you set this value, the
    # more strict the filtering will be, and more context windows will be rejected.
    SIMILARITY_THRESHOLD_CONTEXT_WINDOW: float = 0.34

    # Define keywords here that will be searched for in the core_text
    # of the raw filings from crawler
    LIST_OF_PHRASES_TO_FILTER_FILINGS_FOR: list = ['NPS', "net promoter score", "nps score", "nps of",
                                                   "net promoter", "net promotor"]
    
    # The reference text for the similarity search. This is the text that the
    # context windows are compared to. Each context window will receive a value,
    # the closer this value is to 1, the closer the text meaning of the context
    # windows is to this text.
    SIMILARITY_REFERENCE_TEXT: str = (
        "net promoter score NPS customer loyalty customer satisfaction "
        "recommend promoters detractors customer experience"
    )

    # Define keywords/phrases here that should EXCLUDE a match even if they contain
    # one of the include phrases above. A sentence match is dropped when the include
    # keyword only appears as part of one of these excluded phrases. If the sentence
    # also contains a standalone include keyword elsewhere, the match is kept.
    LIST_OF_PHRASES_TO_EXCLUDE: list = [
        "NEW PRODUCT SALES TO TOTAL PRODUCT SALES RATIO (NPS)",
        "NPS Reservation System",
        "NPS Submit software",
        "Nationwide Payment Solutions",
        "NPS Pharmaceuticals",
        "Netezza Performance Server",
        "National Processing Services",
        "Nano-Pulse Stimulation",
        "NPS Reservation System procurement",
        "Net Power Solutions, LLC (“NPS”),",
        "NPSAX",
        "National Prearranged Services",
        "NPS (Network Payment System)",
        "NetBank Payment Systems, Inc. (“NPS”),",
        "The National Park Service’s (“NPS”)",
        "“Novation Proprietary Services” or “NPS”",
        "Neah Power Systems",
        "SNPS",
        "NPS-KBIC PEF",
        "National Product Services",
        "natural products and supplements",
        "National Partnerships",
        "Networked Products & Services",
        "NPS Services",
        "Navitaire Professional Services",
        "National Production Services",
        "National Product Supply System",
        "Nephrology Practice Solutions",
        "network processors",
        "NetApp Private Storage",
        "NPS Purchase Price",
        "NPS 2.X",
        "Netezza"
        ]
    
    # If any of the above keywords are found, define here the number of sentences
    # to include before and after the keyword
    AMOUNT_SENTENCES_INCLUDED_BEFORE: int = 2
    AMOUNT_SENTENCES_INCLUDED_AFTER: int = 2
    MAX_CONTEXT_CHARS_BEFORE_KEYWORD: int = 600
    MAX_CONTEXT_CHARS_AFTER_KEYWORD: int = 600

    # Similarity Search Model
    SIMILARITY_EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"

    """ Classification CONFIG """
    # Ground-truth CSV train/test split: same random_state and test_size for evaluate, train,
    # and few-shot sampling (training fold only for examples).
    CLASSIFICATION_RANDOM_SEED: int = 42
    CLASSIFICATION_GROUND_TRUTH_TEST_SIZE: float = 0.5
    # Few-shot examples taken from the training fold of category.csv_path.
    # None disables auto-generation when examples=None is passed to ClassificationCategory.
    CLASSIFICATION_FEW_SHOT_NUM_EXAMPLES: int | None = 8
    CLASSIFICATION_FEW_SHOT_TEXT_COLUMN: str = "snippet_text_short"
    # Shuffles rows within the training fold only; does not change the train/test boundary.
    CLASSIFICATION_FEW_SHOT_SAMPLE_SEED: int = 43

    CLASSIFICATION_CACHE_DIR = ROOT_DIR / "src" / "nps_crawling" / "classification" / "cache"
    CLASSIFICATION_CONFIG_DIR = ROOT_DIR / "src" / "nps_crawling" / "classification" / "configurations"

    # When True: category configs are ``categories/<Name>.json`` (no per-name subfolder / hash file).
    # Model configs are ``<ClassName>__<ModelName>.json`` directly under CLASSIFICATION_CONFIG_DIR
    # (no ``<model_name>/<hash>.json`` folder). When False, the previous hash-based layout is used.
    # Can be overridden with env ``CLASSIFICATION_CONFIG_USE_NAME_FILES=1``.
    CLASSIFICATION_CONFIG_USE_NAME_FILES: bool = os.getenv(
        "CLASSIFICATION_CONFIG_USE_NAME_FILES", "0"
    ) == "1"
    nps_category_file = ROOT_DIR / "src" / "nps_crawling" / "classification" / "configurations" / "categories" / "NPS Category" / "c0b1409c1550fcafe2a84875f32bb495385beac0eccf6d09d7e9eac4c266c1f7.json"
    nps_value_category_file = ROOT_DIR / "src" / "nps_crawling" / "classification" / "configurations" / "categories" / "NPS Value Category" / "12b0b9acf27aee693b1d518d68a4b6e9481a53fb55245ab4f08e7c50274f433b.json"
    has_numeric_nps_file = ROOT_DIR / "src" / "nps_crawling" / "classification" / "configurations" / "categories" / "Has Numeric NPS" / "ee63ed22edbeb29b02a976cfdd209f172cff421b5bde2009e1a0c0193f83a38f.json"
    qwen_llm_file = ROOT_DIR / "src" / "nps_crawling" / "classification" / "configurations" / "Qwen3-8B" / "6cd28608db45079139f438ef355a2f901be42efb24f9a4ae1155ebbfa8d957ff.json"
    qwen_svm_file = ROOT_DIR / "src" / "nps_crawling" / "classification" / "configurations" / "Qwen3-Embedding-4B" / "c7d19631b6aeaf2445204a81e778ec2d639ba3c7b02be9416c61e98c5245f3a6.json"
    CLASSIFICATION_CONFIG = {
        str(nps_category_file):str(qwen_svm_file),
        str(has_numeric_nps_file):str(qwen_svm_file),
        str(nps_value_category_file):str(qwen_llm_file)
    }

    # Load Category properties dynamically from classification configurations
    PROJECT_CATEGORIES: list[dict] = []
    for _cat_path in CLASSIFICATION_CONFIG.keys():
        _path = Path(_cat_path)
        if _path.exists():
            try:
                with open(_path, "r", encoding="utf-8") as _f:
                    _data = json.load(_f)
                    for _prop in _data.get("properties", []):
                        _found = False
                        for _x in PROJECT_CATEGORIES:
                            if _x["name"] == _prop["name"]:
                                _found = True
                                break
                        if not _found:
                            PROJECT_CATEGORIES.append({
                                "name": _prop["name"],
                                "type": _prop["type"]
                            })
            except Exception:
                pass
    
    CRAWLER_GLOBAL_LIMIT: int = -1 
    CRAWLER_RECOVERY_ATTEMPTS: int = 10
    CRAWLER_RECOVERY_TIMEOUT: int = 5
    CRAWLER_DRY_RUN: bool = False
    CRAWLER_DELAY: float = 0.1
    CRAWLER_STATS_DUMP: bool = False

    REQUEST_USER_AGENT: str = "user.name@email.com"