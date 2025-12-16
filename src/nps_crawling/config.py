"""Configuration module for NPS Crawling project."""

from pathlib import Path


class Config:
    """PATHS."""
    ROOT_DIR = Path.cwd()
    DATA_PATH = ROOT_DIR / "data"

    RAW_PARQUET_PATH_CRAWLER = DATA_PATH / "parquet_raw"
    NPS_CONTEXT_PARQUET_PATH = DATA_PATH / "nps_context_dataset"
    NPS_CLASSIFIED_CSV = DATA_PATH / "nps_classified_csv"

    DATA_PATH.mkdir(parents=True, exist_ok=True)
    RAW_PARQUET_PATH_CRAWLER.mkdir(parents=True, exist_ok=True)
    NPS_CONTEXT_PARQUET_PATH.mkdir(parents=True, exist_ok=True)
    NPS_CLASSIFIED_CSV.mkdir(parents=True, exist_ok=True)

    """ FILES """
    RAW_PARQUET_FILE_CRAWLER = "nps_filings.parquet"

    """ PRE PROCESSING CONFIG """
    # define the batch size of how many filing should run through data processing pipeline at once
    FILINGS_PASSED_THROUGH_PROCESS_AT_ONCE: int = 2  # 2 just to simulate batch processing, will be way higher

    # define what phrases to filter in text here
    LIST_OF_PHRASES_TO_FILTER_FILINGS_FOR: list = ['NPS', "net promoter score", "nps score", "nps of",
                                                   "customer satisfaction score", "customer loyalty metric",
                                                   "likelihood to recommend"]

    # define the size of the context window here. how many sentences before and after should be included
    AMOUNT_SENTENCES_INCLUDED_BEFORE: int = 2
    AMOUNT_SENTENCES_INCLUDED_AFTER: int = 2

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