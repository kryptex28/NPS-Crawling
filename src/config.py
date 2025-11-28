from pathlib import Path

class Config:

    """ PATHS """
    ROOT_DIR = Path.cwd()
    DATA_PATH = ROOT_DIR / "data"

    RAW_JSON_PATH_CRAWLER = DATA_PATH / "jsonl_raw"
    NPS_CONTEXT_PARQUET_PATH = DATA_PATH / "nps_context_dataset"

    DATA_PATH.mkdir(parents=True, exist_ok=True)
    RAW_JSON_PATH_CRAWLER.mkdir(parents=True, exist_ok=True)
    NPS_CONTEXT_PARQUET_PATH.mkdir(parents=True, exist_ok=True)

    """ FILES """
    RAW_JSON_FILE_CRAWLER = "nps_filings.jsonl"

    """ PRE PROCESSING CONFIG """
    # define the batch size of how many filing should run through data processing pipeline at once
    FILINGS_PASSED_THROUGH_PROCESS_AT_ONCE: int = 2 # 2 just to simulate batch processing, will be way higher

    # define what phrases to filter in text here
    LIST_OF_PHRASES_TO_FILTER_FILINGS_FOR: list = ['NPS', "net promoter score", "nps score", "nps of",
                                                   "customer satisfaction score", "customer loyalty metric", 
                                                   "likelihood to recommend"]
    
    # define the size of the context window here. how many sentences before and after should be included
    AMOUNT_SENTENCES_INCLUDED_BEFORE: int = 2
    AMOUNT_SENTENCES_INCLUDED_AFTER: int = 2