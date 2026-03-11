"""Configuration module for NPS Crawling project."""

from pathlib import Path


class Config:
    """PATHS."""
    ROOT_DIR = Path.cwd()
    DATA_PATH = ROOT_DIR / "data"

    RAW_JSON_PATH_CRAWLER = DATA_PATH / "json_raw"
    NPS_CONTEXT_JSON_PATH = DATA_PATH / "json_processed"
    NPS_CLASSIFIED_JSON = DATA_PATH / "json_classified"
    NPS_REJECTED_JSON_PATH = DATA_PATH / "json_reject"

    DATA_PATH.mkdir(parents=True, exist_ok=True)
    RAW_JSON_PATH_CRAWLER.mkdir(parents=True, exist_ok=True)
    NPS_CONTEXT_JSON_PATH.mkdir(parents=True, exist_ok=True)
    NPS_CLASSIFIED_JSON.mkdir(parents=True, exist_ok=True)
    NPS_REJECTED_JSON_PATH.mkdir(parents=True, exist_ok=True)

    """ FILES """
    RAW_PARQUET_FILE_CRAWLER = "nps_filings.parquet"

    """ PRE PROCESSING CONFIG """
    # define the batch size of how many filing should run through data processing pipeline at once
    FILINGS_PASSED_THROUGH_PROCESS_AT_ONCE: int = 2  # 2 just to simulate batch processing, will be way higher

    
    LIST_OF_PHRASES_TO_FILTER_FILINGS_FOR: list = ['NPS', "net promoter score", "nps score", "nps of",
                                                   "customer satisfaction score", "customer loyalty metric",
                                                   "likelihood to recommend"]

    AMOUNT_SENTENCES_INCLUDED_BEFORE: int = 2
    AMOUNT_SENTENCES_INCLUDED_AFTER: int = 2

    """ SIMILARITY SEARCH CONFIG """
    SIMILARITY_EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    SIMILARITY_REFERENCE_TEXT: str = (
        "Net Promoter Score (NPS) is a customer satisfaction and loyalty metric "
        "that measures how likely customers are to recommend a company's products "
        "or services to others on a scale from 0 to 10. Companies report NPS scores, "
        "track NPS improvements, and benchmark NPS against competitors."
    )
   
    SIMILARITY_THRESHOLD_CONTEXT_WINDOW: float = 0.2
    SIMILARITY_THRESHOLD_DOCUMENT_AVG: float = 0.2

    """ LLM CONFIG """
    # OLLAMA
    OLLAMA_PERSONA: str = (
            "You are a corporate-disclosure text classifier.\n"
            "Task: Given an input context window, assign exactly ONE category describing how NPS is referenced:\n"
            "1) Score reporting: the company discloses an NPS value or clearly reports its NPS performance.\n"
            "2) Improvement initiatives: efforts or initiatives intended to improve NPS.\n"
            "3) Benchmarking / competition: NPS compared to competitors, peers, or industry averages.\n"
            "4) General statements: NPS mentioned as an important metric without a score, initiative, or comparison.\n"
            "Output: Return 1–2 short lines: first line 'Category: <one of the four labels exactly as written above>'. "
            "Second line optional 'Reason: <brief why>'. Keep it concise."
        )

    MODEL = "SVM"  # Options: "SVM", "Ollama"
