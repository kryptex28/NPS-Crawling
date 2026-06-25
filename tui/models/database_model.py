from dataclasses import dataclass

from nps_crawling.db.db_adapter import DbAdapter

class DatabaseModel():

    def __init__(self) -> None:
        self.db = DbAdapter()

    def get_all_filings(self) -> list[dict]:
        return self.db.get_all_filings()