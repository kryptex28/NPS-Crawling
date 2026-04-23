"""Configuration module for NPS Crawling project."""

import subprocess
from pathlib import Path
import os
from dotenv import load_dotenv

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

    # ---------------------------------------------------------------------------
    # Local Mode
    # ---------------------------------------------------------------------------
    # Wenn True: Die Docker-Postgres (docker/database/docker-compose.yml) wird
    # beim Programmstart automatisch hochgefahren und als Datenbank verwendet.
    # Wenn False: Die Umgebungsvariable POSTGRES_ENGINE muss gesetzt sein.

    # .env LOCAL_MODE=1 to enable local mode, .env LOCAL_MODE=0 to disable local mode
    # defaults to False if not set to not interfere with existing server setup
    LOCAL_MODE: bool = os.getenv("LOCAL_MODE", "0") == "1"

    # Verbindungsstring für die lokale Docker-Postgres (user:password@host:port/db)
    LOCAL_DB_CONNECTION: str = "crawler:crawler@localhost:5432/crawler"
    # ---------------------------------------------------------------------------

    # Database Settings
    DATABASE_TABLE_NAME: str = "nps_filings_new"

    # Define experiment name, preprocessing version and classification version.
    # For PREPROCESSING:
    # Will check if data/json_processed/<PREPROCESSING_VERSION> already exists.
    # If so, preprocessing will be skipped entirely.
    # If not, it will create it and save the preprocessed JSONs there with the
    # configurations set below.
    PREPROCESSING_VERSION: str = "version_3"
    CLASSIFICATION_VERSION: str = "version_3"

    # Base directories
    RAW_JSON_PATH_CRAWLER = DATA_PATH / "json_raw"
    PROCESSED_BASE_PATH = DATA_PATH / "json_processed"
    REJECTED_BASE_PATH = DATA_PATH / "json_rejected"
    CLASSIFIED_BASE_PATH = DATA_PATH / "json_classified"

    # Experiment-specific directories
    NPS_CONTEXT_JSON_PATH = PROCESSED_BASE_PATH / PREPROCESSING_VERSION
    NPS_REJECTED_JSON_PATH = REJECTED_BASE_PATH / PREPROCESSING_VERSION
    NPS_CLASSIFIED_JSON = CLASSIFIED_BASE_PATH / CLASSIFICATION_VERSION

    # Create base directories (always needed)
    DATA_PATH.mkdir(parents=True, exist_ok=True)
    RAW_JSON_PATH_CRAWLER.mkdir(parents=True, exist_ok=True)
    (RAW_JSON_PATH_CRAWLER / "files").mkdir(parents=True, exist_ok=True)
    (RAW_JSON_PATH_CRAWLER / "crawl_reports").mkdir(parents=True, exist_ok=True)
    PROCESSED_BASE_PATH.mkdir(parents=True, exist_ok=True)
    REJECTED_BASE_PATH.mkdir(parents=True, exist_ok=True)
    CLASSIFIED_BASE_PATH.mkdir(parents=True, exist_ok=True)
    # Note: Version-specific dirs (NPS_CONTEXT_JSON_PATH, NPS_REJECTED_JSON_PATH,
    # NPS_CLASSIFIED_JSON) are created lazily by the respective pipeline constructors.

    """ PREPROCESSING CONFIG """
    # When set, only filings whose db keywords list is exactly [SINGLE_KEYWORD_FILTER]
    # are preprocessed. Filings with additional keywords are skipped.
    # Set to None to disable this filter and process all filings.
    SINGLE_KEYWORD_FILTER: str | None = None
    # If below variable is set to True, it will exclude filings that contain the SINGLE_KEYWORD_FILTER.
    # If set to False, it will include filings that contain the SINGLE_KEYWORD_FILTER and skip all others.
    SINGLE_KEYWORD_FILTER_EXCLUDE: bool = False

    # Define keywords here that will be searched for in the core_text
    # of the raw filings from crawler
    LIST_OF_PHRASES_TO_FILTER_FILINGS_FOR: list = ['NPS', "net promoter score", "nps score", "nps of",
                                                   "net promoter"]

    # Define keywords/phrases here that should EXCLUDE a match even if they contain
    # one of the include phrases above. A sentence match is dropped when the include
    # keyword only appears as part of one of these excluded phrases. If the sentence
    # also contains a standalone include keyword elsewhere, the match is kept.
    LIST_OF_PHRASES_TO_EXCLUDE: list = [
        "NEW PRODUCT SALES TO TOTAL PRODUCT SALES RATIO (NPS)",
        "NPS Reservation System",
        "NPS Submit software",
    ]
    # If any of the above keywords are found, define here the number of sentences
    # to include before and after the keyword
    AMOUNT_SENTENCES_INCLUDED_BEFORE: int = 2
    AMOUNT_SENTENCES_INCLUDED_AFTER: int = 2
    MAX_CONTEXT_CHARS_BEFORE_KEYWORD: int = 600
    MAX_CONTEXT_CHARS_AFTER_KEYWORD: int = 600

    # Similarity Search Model
    SIMILARITY_EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"

    # The reference text for the similarity search. This is the text that the
    # context windows are compared to. Each context window will receive a value,
    # the closer this value is to 1, the closer the text meaning of the context
    # windows is to this text.
    SIMILARITY_REFERENCE_TEXT: str = (
        "Net Promoter Score (NPS) is a key performance indicator (KPI) and customer "
        "loyalty metric used by management to measure customer satisfaction, brand "
        "health, and the likelihood of customers to recommend a company's products "
        "or services. Companies track NPS scores to predict customer retention and "
        "churn, report NPS improvements to investors as an indicator of future organic "
        "growth, and benchmark NPS against competitors to evaluate market position."
    )
    # Define Threshold for similarity search here. Context windows that fall below
    # this value will be filtered out. This means the higher you set this value, the
    # more strict the filtering will be, and more context windows will be rejected.
    SIMILARITY_THRESHOLD_CONTEXT_WINDOW: float = 0.2

    """ Classification CONFIG """
    # OLLAMA
    OLLAMA_PERSONA: str = (
            "You are a corporate-disclosure text classifier.\n"
            "Task: Given an input context window, assign exactly ONE category describing how NPS is referenced:\n"
            "1) BENCHMARK_COMPARISON: The text compares the company’s Net Promoter Score with external or industry benchmarks.\n"
            "2) CUSTOMER_CASE_EVIDENCE: The text uses the Net Promoter Score as evidence in customer examples or use cases..\n"
            "3) KPI_DISCLOSURE: The text reports the Net Promoter Score as a quantitative performance metric.\n"
            "4) METHODOLOGY_DEFINITION: The text defines or explains what the Net Promoter Score is or how it is calculated."
            "5) MGMT_COMPENSATION_GOVERNANCE: The text links the Net Promoter Score to management compensation, incentives, or governance.\n"
            "6) QUALITATIVE_ONLY: The text mentions the Net Promoter Score only in a qualitative or descriptive way without numbers.\n"
            "7) TARGET_OUTLOOK: The text discusses targets, goals, or future expectations for the Net Promoter Score.\n"
            "Output: The chosen category label and nothing else."
        )

    MODEL = "SVM"  # Options: "SVM", "Ollama"
