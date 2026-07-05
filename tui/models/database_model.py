
from nps_crawling.db.db_adapter import DbAdapter

class DatabaseModel():

    def __init__(self) -> None:
        """Initialize the DatabaseModel instance."""
        pass

    def get_all_filings(self) -> list[dict]:
        """Fetch and return all crawled filings from the database."""
        db = DbAdapter()
        db.ensure_table_exists()
        return db.get_all_filings()