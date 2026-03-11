import os

from sqlalchemy import create_engine, text

from nps_crawling.db.nps_filings_db import NpsFilingsDB


class DbAdapter:
    """
    Adapter class for simplified interaction with the nps_filings table.
    Wraps around NpsFilingsDB to provide specific, easy-to-use methods
    for adding filings, checking existence, adding keywords, and retrieving filings.
    """

    def __init__(self, connection_string: str = None):
        """
        Initializes the database connection and the underlying DB wrapper.
        If no connection string is provided, falls back to the POSTGRES_ENGINE env variable.
        """
        if not connection_string:
            connection_string = os.environ.get('POSTGRES_ENGINE')
            if not connection_string:
                raise ValueError("No connection string provided and POSTGRES_ENGINE environment variable is not set.")

        self.engine = create_engine(f"postgresql+psycopg2://{connection_string}")
        self._db = NpsFilingsDB(self.engine)
        self.table_name = self._db.TABLE

    def add_filing(self, filing_id: str, **kwargs) -> None:
        """
        Adds or updates a new filing in the database.

        Args:
            filing_id (str): The unique identifier for the filing.
            **kwargs: Other fields matching the database schema
                      (e.g., ciks, display_names, nps_relevant, path_to_raw, etc.)
        """
        # We pass the unpacked dictionary to upsert_filing.
        # NpsFilingsDB will handle matching them to columns or using defaults.
        self._db.upsert_filing(id=filing_id, **kwargs)

    def filing_exists(self, filing_id: str) -> bool:
        """
        Checks if a filing with the given ID already exists in the database.

        Args:
            filing_id (str): The unique identifier for the filing.

        Returns:
            bool: True if the filing exists, False otherwise.
        """
        stmt = text(f"SELECT EXISTS(SELECT 1 FROM {self.table_name} WHERE id = :id)")
        with self.engine.connect() as conn:
            return conn.execute(stmt, {"id": filing_id}).scalar()

    def add_keyword(self, filing_id: str, keyword: str) -> bool:
        """
        Adds a single keyword to the keywords array for a specific filing.
        If the filing does not exist, nothing will be done.

        Args:
            filing_id (str): The unique identifier for the filing.
            keyword (str): The keyword to add.

        Returns:
            bool: True if keyword was successfully added, False if the filing did not exist or the keyword already existed.
        """
        return self._db.add_keyword(id=filing_id, kw=keyword)

    def get_filing(self, filing_id: str) -> dict | None:
        """
        Retrieves all data for a specific filing and returns it as a dictionary.

        Args:
            filing_id (str): The unique identifier for the filing.

        Returns:
            dict | None: A dictionary representation of the row if found, otherwise None.
        """
        stmt = text(f"SELECT * FROM {self.table_name} WHERE id = :id")
        with self.engine.connect() as conn:
            # We use mappings() to get a dictionary-like row object, then convert to a real dict
            row = conn.execute(stmt, {"id": filing_id}).mappings().first()
            if row:
                return dict(row)
            return None

    def update_filing(self, filing_id: str, touch_last_crawled: bool = True, **kwargs) -> bool:
        """
        Updates one or multiple fields for a specific filing.

        Args:
            filing_id (str): The unique identifier for the filing.
            touch_last_crawled (bool): If True, updates the `last_crawled` timestamp. Defaults to True.
            **kwargs: Arbitrary fields to update matching the database schema
                      (e.g., nps_goal_reached=True, nps_value_fix=8.5)

        Returns:
            bool: True if the filing was found and updated, False otherwise.
        """
        rows_affected = self._db.update_fields(filing_id, touch_last_crawled=touch_last_crawled, **kwargs)
        return rows_affected > 0

    # --- Additional helpful retrieval methods ---

    def update_path_to_raw(self, filing_id: str, path: str) -> bool:
        """
        Updates only the `path_to_raw` field for a specific filing without modifying `last_crawled`.
        """
        rows_affected = self._db.update_fields(filing_id, touch_last_crawled=False, path_to_raw=path)
        return rows_affected > 0

    def update_path_to_preprocessed(self, filing_id: str, path: str) -> bool:
        """
        Updates only the `path_to_preprocessed` field for a specific filing without modifying `last_crawled`.
        """
        rows_affected = self._db.update_fields(filing_id, touch_last_crawled=False, path_to_preprocessed=path)
        return rows_affected > 0

    def update_path_to_classified(self, filing_id: str, path: str) -> bool:
        """
        Updates only the `path_to_classified` field for a specific filing without modifying `last_crawled`.
        """
        rows_affected = self._db.update_fields(filing_id, touch_last_crawled=False, path_to_classified=path)
        return rows_affected > 0

    def get_all_filings(self, limit: int = 100) -> list[dict]:
        """
        Retrieves a list of up to `limit` filings.

        Args:
            limit (int): The maximum number of filings to retrieve. Defaults to 100.

        Returns:
            list[dict]: A list of dictionary representations of the rows.
        """
        stmt = text(f"SELECT * FROM {self.table_name} LIMIT :limit")
        with self.engine.connect() as conn:
            rows = conn.execute(stmt, {"limit": limit}).mappings().all()
            return [dict(row) for row in rows]

    def get_filing_paths(self, filing_id: str) -> dict | None:
        """
        A convenience method to just retrieve the file paths for a filing.
        """
        stmt = text(f"""
            SELECT path_to_raw, path_to_preprocessed, path_to_classified
            FROM {self.table_name}
            WHERE id = :id
        """)
        with self.engine.connect() as conn:
            row = conn.execute(stmt, {"id": filing_id}).mappings().first()
            if row:
                return dict(row)
            return None
