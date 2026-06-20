import os
from typing import Any

from sqlalchemy import create_engine, text

from nps_crawling.config import Config
from nps_crawling.db.nps_filings_db import NpsFilingsDB


class DbAdapter:
    """
    Adapter class for simplified interaction with the nps_filings table.
    Wraps around NpsFilingsDB to provide specific, easy-to-use methods
    for adding filings, checking existence, adding keywords, and retrieving filings.
    """

    def __init__(self, connection_string: str = None) -> None:
        """
        Initializes the database connection and the underlying DB wrapper.

        Priority for the connection string:
        1. Explicit ``connection_string`` argument
        2. ``Config.LOCAL_DB_CONNECTION`` when ``Config.LOCAL_MODE`` is True
        3. ``POSTGRES_ENGINE`` environment variable
        """
        if not connection_string:
            if Config.LOCAL_MODE:
                connection_string = Config.LOCAL_DB_CONNECTION
            else:
                connection_string = os.environ.get('POSTGRES_ENGINE')
                if not connection_string:
                    raise ValueError(
                        "LOCAL_MODE=False und die Umgebungsvariable POSTGRES_ENGINE ist nicht gesetzt.",
                    )

        self.engine = create_engine(f"postgresql+psycopg2://{connection_string}")
        self._db = NpsFilingsDB(self.engine)
        self.table_name = self._db.TABLE

    def ensure_table_exists(
        self,
        include_classifications: bool = False,
        classification_properties: dict[str, str] | None = None
    ) -> None:
        """Erstellt die Tabelle falls sie noch nicht existiert (CREATE TABLE IF NOT EXISTS)."""
        create_stmt = text(f"""
        CREATE TABLE IF NOT EXISTS {self.table_name} (
            id VARCHAR PRIMARY KEY,

            -- SEC Metadata
            ciks TEXT[],
            ticker TEXT[],
            period_ending DATE,
            display_names TEXT[],
            root_forms TEXT[],
            file_date DATE,
            form VARCHAR,
            adsh VARCHAR,
            file_type VARCHAR,
            file_description TEXT,
            film_num TEXT[],

            -- Extraction/Processing Metadata
            keywords TEXT[],
            blacklisted BOOLEAN DEFAULT FALSE,
            project_relevant BOOLEAN,

            -- File Paths
            path_to_raw VARCHAR,
            path_to_preprocessed VARCHAR,
            path_to_classified VARCHAR,
            url VARCHAR,

            -- Crawl Tracking
            last_crawled TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
        """)
        
        type_mapping = {
            "boolean": "BOOLEAN",
            "float": "DOUBLE PRECISION",
            "int": "INTEGER",
            "integer": "INTEGER"
        }

        if classification_properties is not None:
            category_columns = []
            for col_name, col_type in classification_properties.items():
                db_type = type_mapping.get(col_type.lower(), "BOOLEAN")
                category_columns.append(f'"{col_name}" {db_type}')
            cols_sql = ",\n            ".join(category_columns)
        else:
            cols_sql = Config.get_classification_columns_sql()

        cols_sql_part = f"\n            {cols_sql},\n" if cols_sql else ""
        create_stmt_classifications = text(f"""
        CREATE TABLE IF NOT EXISTS {self.table_name}_classifications (
            id SERIAL PRIMARY KEY,
            filing_id VARCHAR REFERENCES {self.table_name}(id) ON DELETE CASCADE,
            experiment_version VARCHAR NOT NULL,{cols_sql_part}
            classified_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            UNIQUE (filing_id, experiment_version)
        );
        """)
        create_stmt_preprocessing = text(f"""
        CREATE TABLE IF NOT EXISTS {self.table_name}_preprocessing (
            id SERIAL PRIMARY KEY,
            filing_id VARCHAR REFERENCES {self.table_name}(id) ON DELETE CASCADE,
            preprocessing_version VARCHAR NOT NULL,
            
            project_relevant BOOLEAN NOT NULL,
            path_to_preprocessed VARCHAR,
            
            processed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            UNIQUE (filing_id, preprocessing_version)
        );
        """)

        with self.engine.begin() as conn:
            conn.execute(create_stmt)
            conn.execute(create_stmt_preprocessing)
            if include_classifications and Config.ACTIVE_PROJECT:
                conn.execute(create_stmt_classifications)
                
                # Check for any new categories in JSON that are not yet in the DB table
                existing_cols_stmt = text(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_name = :table_name"
                )
                class_table = f"{self.table_name}_classifications".lower()
                existing_cols = {
                    row["column_name"]
                    for row in conn.execute(existing_cols_stmt, {"table_name": class_table}).mappings().all()
                }
                
                properties_to_check = (
                    classification_properties
                    if classification_properties is not None
                    else {cat["name"]: cat["type"] for cat in Config.PROJECT_CATEGORIES}
                )
                
                for col_name, col_type in properties_to_check.items():
                    if col_name not in existing_cols:
                        col_type = type_mapping.get(col_type.lower(), "BOOLEAN")
                        alter_stmt = text(
                            f'ALTER TABLE {self.table_name}_classifications '
                            f'ADD COLUMN "{col_name}" {col_type};'
                        )
                        conn.execute(alter_stmt)
                        print(f"Spalte '{col_name}' ({col_type}) dynamisch zur Tabelle '{self.table_name}_classifications' hinzugefuegt.", flush=True)
                        
                print(f"Tabellen '{self.table_name}', '{self.table_name}_preprocessing' und '{self.table_name}_classifications' gecheckt/erstellt.", flush=True)
            else:
                print(f"Tabellen '{self.table_name}' und '{self.table_name}_preprocessing' gecheckt/erstellt (Klassifikations-Tabelle uebersprungen).", flush=True)

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

    def return_keywords(self, filing_id: str) -> list[str]:
        """
        Retrieves all keywords for a specific filing.

        Args:
            filing_id (str): The unique identifier for the filing.

        Returns:
            list[str]: A list of keywords associated with the filing.
        """
        keywords = self.get_filing_field(filing_id, "keywords")
        return keywords if keywords is not None else []

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

    def get_filing_field(self, filing_id: str, field_name: str) -> Any:
        """
        Retrieves a specific field for a given filing.

        Args:
            filing_id (str): The unique identifier for the filing.
            field_name (str): The name of the field to retrieve.

        Returns:
            Any: The value of the field, or None if the filing is not found.
        """
        return self._db.get_field(id=filing_id, field=field_name)

    def update_filing(self, filing_id: str, touch_last_crawled: bool = True, **kwargs) -> bool:
        """
        Updates one or multiple fields for a specific filing.

        Args:
            filing_id (str): The unique identifier for the filing.
            touch_last_crawled (bool): If True, updates the `last_crawled` timestamp. Defaults to True.
            **kwargs: Arbitrary fields to update matching the database schema
                      (e.g., NPS_GOAL_REACHED=True, nps_value_fix=8.5)

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

    def update_url(self, filing_id: str, url: str) -> bool:
        """
        Updates only the `url` field for a specific filing without modifying `last_crawled`.
        """
        rows_affected = self._db.update_fields(filing_id, touch_last_crawled=False, url=url)
        return rows_affected > 0

    def get_all_filings(self, limit: int | None = None) -> list[dict]:
        """
        Retrieves a list of filings with all meta information.

        Args:
            limit (int | None): The maximum number of filings to retrieve. If None, retrieves ALL filings. Defaults to None.

        Returns:
            list[dict]: A list of dictionary representations of the rows.
        """
        if limit is not None:
            stmt = text(f"SELECT * FROM {self.table_name} LIMIT :limit")
            params = {"limit": limit}
        else:
            stmt = text(f"SELECT * FROM {self.table_name}")
            params = {}
            
        with self.engine.connect() as conn:
            rows = conn.execute(stmt, params).mappings().all()
            return [dict(row) for row in rows]

    def get_filings_by_keyword(self, keyword: str, strict: bool = False) -> list[dict]:
        """
        Retrieves all filings that contain a specific keyword, including all meta information.

        Args:
            keyword (str): The keyword to search for.
            strict (bool): If True, only returns filings where this is the ONLY keyword. 
                           If False, returns all filings containing this keyword.

        Returns:
            list[dict]: A list of dictionary representations of the rows.
        """
        quoted_keyword = f'"{keyword}"'
        
        if strict:
            stmt = text(f"SELECT * FROM {self.table_name} WHERE array_length(keywords, 1) = 1 AND (keywords[1] = :keyword OR keywords[1] = :quoted_keyword)")
        else:
            stmt = text(f"SELECT * FROM {self.table_name} WHERE :keyword = ANY(keywords) OR :quoted_keyword = ANY(keywords)")
            
        with self.engine.connect() as conn:
            rows = conn.execute(stmt, {"keyword": keyword, "quoted_keyword": quoted_keyword}).mappings().all()
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

    def upsert_classification(self, filing_id: str, version: str, path_to_classified: str | None = None, allowed_cols: set[str] | None = None, **kwargs) -> None:
        """
        Upserts a classification result for a specific filing and experiment version.
        This also updates the main filings table with the classified path.
        
        Args:
            filing_id (str): The unique identifier for the filing.
            version (str): The classification experiment version.
            path_to_classified (str | None): Path to the classified JSON file.
            allowed_cols (set[str] | None): Set of allowed column names.
            **kwargs: Classification category flags mapping to db columns.
        """
        self._db.upsert_classification(filing_id, version, path_to_classified, allowed_cols=allowed_cols, **kwargs)

    def get_classifications(self, filing_id: str) -> list[dict]:
        """
        Retrieves all classification results for a specific filing.
        """
        return self._db.get_classifications(filing_id)

    def upsert_preprocessing_result(self, filing_id: str, version: str, project_relevant: bool, path_to_preprocessed: str | None = None) -> None:
        """
        Upserts preprocessing results for a specific filing and experiment version.
        This updates both the versioned preprocessing table and the main filings table.
        
        Args:
            filing_id (str): The unique identifier for the filing.
            version (str): The preprocessing experiment version.
            project_relevant (bool): Whether the filing is considered relevant.
            path_to_preprocessed (str | None): Path to the preprocessed JSON file.
        """
        self._db.upsert_preprocessing_result(filing_id, version, project_relevant, path_to_preprocessed)
