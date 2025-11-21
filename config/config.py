from pathlib import Path

class Config:

    """ PATHS """
    ROOT_DIR = Path.cwd()
    DATA_PATH = ROOT_DIR / "Data"

    RAW_JSON_PATH_CRAWLER = DATA_PATH / "json_raw"

    DATA_PATH.mkdir(parents=True, exist_ok=True)
    RAW_JSON_PATH_CRAWLER.mkdir(parents=True, exist_ok=True)

    """ FILES """
    RAW_JSON_FILE_FROM_CRAWLER = "nps_filings.json"

    FILINGS_PASSED_THROUGH_PROCESS_AT_ONCE: int = 10
    
    pass