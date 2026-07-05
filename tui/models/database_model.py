from dataclasses import dataclass

from nps_crawling.db.db_adapter import DbAdapter

class DatabaseModel():

    def __init__(self) -> None:
        pass

    def get_all_filings(self) -> list[dict]:
        db = DbAdapter()
        db.ensure_table_exists()
        return db.get_all_filings()