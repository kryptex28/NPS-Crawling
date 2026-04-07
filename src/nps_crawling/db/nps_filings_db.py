# nps_filings_db.py
from __future__ import annotations

import json
from typing import Any, Literal

from sqlalchemy import Engine, text

from nps_crawling.config import Config


class NpsFilingsDB:
    """Database access layer for NPS filings."""
    # Name of the target PostgreSQL table.
    TABLE = Config.DATABASE_TABLE_NAME

    # Columns stored as PostgreSQL text arrays (TEXT[]).
    _ARRAY_COLS = {"ciks", "display_names", "root_forms", "film_num", "keywords"}

    # Columns that are allowed to be updated via update_fields().
    _UPDATABLE_COLS = {
        "ciks",
        "period_ending",
        "display_names",
        "root_forms",
        "file_date",
        "form",
        "adsh",
        "file_type",
        "file_description",
        "film_num",
        "keywords",
        "last_crawled",
        "blacklisted",
        "nps_relevant",
        "path_to_raw",
        "path_to_preprocessed",
        "path_to_classified",
        "url",
    }

    def __init__(self, engine: Engine) -> None:
        """Initialize NpsFilingsDB with a SQLAlchemy Engine."""
        # Store the SQLAlchemy Engine used for all DB operations.
        self.engine = engine

    def upsert_filing(
        self,
        id: str,
        *,
        ciks: list[str] | None = None,
        period_ending=None,  # datetime.date | None
        display_names: list[str] | None = None,
        root_forms: list[str] | None = None,
        file_date=None,  # datetime.date | None
        form: str | None = None,
        adsh: str | None = None,
        file_type: str | None = None,
        file_description: str | None = None,
        film_num: list[str] | None = None,
        keywords: list[str] | None = None,
        blacklisted: bool = False,
        nps_relevant: bool | None = None,
        meta: dict[str, Any] | None = None,
        path_to_raw: str | None = None,
        path_to_preprocessed: str | None = None,
        path_to_classified: str | None = None,
        url: str | None = None,
    ) -> None:

        stmt = text(f"""
        INSERT INTO {self.TABLE} (
          id, ciks, period_ending, display_names, root_forms, file_date, form, adsh,
          file_type, file_description, film_num, keywords,
          blacklisted, nps_relevant, path_to_raw, path_to_preprocessed, path_to_classified, url
        )
        VALUES (
          :id,
          COALESCE(CAST(:ciks AS text[]), CAST(ARRAY[] AS text[])),
          :period_ending,
          COALESCE(CAST(:display_names AS text[]), CAST(ARRAY[] AS text[])),
          COALESCE(CAST(:root_forms AS text[]), CAST(ARRAY[] AS text[])),
          :file_date, :form, :adsh,
          :file_type, :file_description,
          COALESCE(CAST(:film_num AS text[]), CAST(ARRAY[] AS text[])),
          COALESCE(CAST(:film_num AS text[]), CAST(ARRAY[] AS text[])),
          COALESCE(CAST(:keywords AS text[]), CAST(ARRAY[] AS text[])),
          :blacklisted, :nps_relevant,
          :path_to_raw, :path_to_preprocessed, :path_to_classified, :url
        )
        ON CONFLICT (id) DO UPDATE
        SET
          -- Update crawl timestamp on every upsert conflict.
          last_crawled     = now(),
          -- "Sticky" booleans: once TRUE, remain TRUE.
          blacklisted      = {self.TABLE}.blacklisted OR EXCLUDED.blacklisted,
          nps_relevant     = {self.TABLE}.nps_relevant OR EXCLUDED.nps_relevant,

          -- Only overwrite paths when a new non-NULL value is provided.
          path_to_raw              = COALESCE(EXCLUDED.path_to_raw, {self.TABLE}.path_to_raw),
          path_to_preprocessed     = COALESCE(EXCLUDED.path_to_preprocessed, {self.TABLE}.path_to_preprocessed),
          path_to_classified       = COALESCE(EXCLUDED.path_to_classified, {self.TABLE}.path_to_classified),
          url                      = COALESCE(EXCLUDED.url, {self.TABLE}.url),

          -- Array fields
          ciks             = CASE WHEN :ciks IS NULL THEN {self.TABLE}.ciks ELSE EXCLUDED.ciks END,
          display_names    = CASE WHEN :display_names IS NULL THEN {self.TABLE}.display_names ELSE EXCLUDED.display_names END,
          root_forms       = CASE WHEN :root_forms IS NULL THEN {self.TABLE}.root_forms ELSE EXCLUDED.root_forms END,
          film_num         = CASE WHEN :film_num IS NULL THEN {self.TABLE}.film_num ELSE EXCLUDED.film_num END,
          keywords         = CASE WHEN :keywords IS NULL THEN {self.TABLE}.keywords ELSE EXCLUDED.keywords END,

          -- Scalar fields
          period_ending    = COALESCE(EXCLUDED.period_ending, {self.TABLE}.period_ending),
          file_date        = COALESCE(EXCLUDED.file_date, {self.TABLE}.file_date),
          form             = COALESCE(EXCLUDED.form, {self.TABLE}.form),
          adsh             = COALESCE(EXCLUDED.adsh, {self.TABLE}.adsh),
          file_type        = COALESCE(EXCLUDED.file_type, {self.TABLE}.file_type),
          file_description = COALESCE(EXCLUDED.file_description, {self.TABLE}.file_description);
        """)

        with self.engine.begin() as conn:
            conn.execute(
                stmt,
                {
                    "id": id,
                    "ciks": ciks,
                    "period_ending": period_ending,
                    "display_names": display_names,
                    "root_forms": root_forms,
                    "file_date": file_date,
                    "form": form,
                    "adsh": adsh,
                    "file_type": file_type,
                    "file_description": file_description,
                    "film_num": film_num,
                    "keywords": keywords,
                    "blacklisted": blacklisted,
                    "nps_relevant": nps_relevant,
                    "path_to_raw": path_to_raw,
                    "path_to_preprocessed": path_to_preprocessed,
                    "path_to_classified": path_to_classified,
                    "url": url,
                },
            )

    def update_fields(
        self,
        id: str,
        *,
        touch_last_crawled: bool = True,
        **fields: Any,
    ) -> int:
        """Update specified fields of an existing filing by id."""
        # No updates requested.
        if not fields:
            return 0

        # Reject attempts to update columns outside the allowed set.
        unknown = set(fields) - self._UPDATABLE_COLS
        if unknown:
            raise ValueError(f"Unknown columns: {sorted(unknown)}")

        # Build a dynamic SET clause so only provided fields are modified.
        set_parts: list[str] = []
        params: dict[str, Any] = {"id": id}

        for col, val in fields.items():
            # Array columns are stored as TEXT[].
            if col in self._ARRAY_COLS:
                if val is None:
                    # Array columns are NOT NULL in the schema; set to empty array instead of NULL.
                    set_parts.append(f"{col} = CAST(ARRAY[] AS text[])")
                else:
                    params[col] = val
                    set_parts.append(f"{col} = CAST(:{col} AS text[])")
                continue

            # For scalar columns, None means set the column to NULL.
            if val is None:
                if col.isupper():
                    set_parts.append(f'"{col}" = NULL')
                else:
                    set_parts.append(f"{col} = NULL")
            else:
                params[col] = val
                if col.isupper():
                    set_parts.append(f'"{col}" = :{col}')
                else:
                    set_parts.append(f"{col} = :{col}")

        # Optionally update last_crawled unless the caller explicitly sets it.
        if touch_last_crawled and "last_crawled" not in fields:
            set_parts.append("last_crawled = now()")

        # Execute the UPDATE and return number of affected rows.
        stmt = text(f"""
        UPDATE {self.TABLE}
        SET {", ".join(set_parts)}
        WHERE id = :id;
        """)

        with self.engine.begin() as conn:
            res = conn.execute(stmt, params)
            return int(res.rowcount or 0)

    def delete_filing(self, id: str) -> bool:
        """Deletes a filing from the database by its ID."""
        stmt = text(f"DELETE FROM {self.TABLE} WHERE id = :id;")
        with self.engine.begin() as conn:
            res = conn.execute(stmt, {"id": id})
            return (res.rowcount or 0) > 0

    def is_blacklisted(self, id: str) -> bool:
        """Checks if a filing is marked as blacklisted."""
        stmt = text(f"SELECT blacklisted FROM {self.TABLE} WHERE id = :id;")
        with self.engine.connect() as conn:
            val = conn.execute(stmt, {"id": id}).scalar_one_or_none()
            return bool(val) if val is not None else False

    def nps_relevant(self, id: str) -> bool:
        """Checks if a filing is marked as relevant for NPS calculations."""
        stmt = text(f"SELECT nps_relevant FROM {self.TABLE} WHERE id = :id;")
        with self.engine.connect() as conn:
            val = conn.execute(stmt, {"id": id}).scalar_one_or_none()
            return bool(val) if val is not None else False

    def classified_exists(self, id: str) -> bool:
        """Checks whether the filing has a classified file path."""
        stmt = text(f"""
        SELECT (path_to_classified IS NOT NULL AND path_to_classified <> '')
        FROM {self.TABLE}
        WHERE id = :id;
        """)
        with self.engine.connect() as conn:
            val = conn.execute(stmt, {"id": id}).scalar_one_or_none()
            return bool(val) if val is not None else False

    def preprocessed_exists(self, id: str) -> bool:
        """Checks whether the filing has a preprocessed file path."""
        stmt = text(f"""
        SELECT (path_to_preprocessed IS NOT NULL AND path_to_preprocessed <> '')
        FROM {self.TABLE}
        WHERE id = :id;
        """)
        with self.engine.connect() as conn:
            val = conn.execute(stmt, {"id": id}).scalar_one_or_none()
            return bool(val) if val is not None else False

    def raw_exists(self, id: str) -> bool:
        """Checks whether the filing has a raw file path."""
        stmt = text(f"""
        SELECT (path_to_raw IS NOT NULL AND path_to_raw <> '')
        FROM {self.TABLE}
        WHERE id = :id;
        """)
        with self.engine.connect() as conn:
            val = conn.execute(stmt, {"id": id}).scalar_one_or_none()
            return bool(val) if val is not None else False

    def blacklist(self, id: str) -> None:
        """Marks a filing as blacklisted, inserting a new record if it does not exist."""
        stmt = text(f"""
        INSERT INTO {self.TABLE} (id, blacklisted)
        VALUES (:id, TRUE)
        ON CONFLICT (id) DO UPDATE
        SET blacklisted = TRUE, last_crawled = now();
        """)
        with self.engine.begin() as conn:
            conn.execute(stmt, {"id": id})

    def add_keyword(self, id: str, kw: str) -> bool:
        """Appends a new keyword to the keywords array for a filing. Returns True if successfully added."""
        stmt = text(f"""
        UPDATE {self.TABLE}
        SET
          keywords = CASE
            WHEN NOT (:kw = ANY(keywords)) THEN array_append(keywords, :kw)
            ELSE keywords
          END,
          last_crawled = now()
        WHERE id = :id
        RETURNING 1;
        """)
        with self.engine.begin() as conn:
            # scalar() returns 1 if row was updated (meaning the keyword was successfully added),
            # or None if row doesn't exist or keyword was already in the array.
            return bool(conn.execute(stmt, {"id": id, "kw": kw}).scalar())

    def get_field(self, id: str, field: str) -> Any:
        """Retrieve a specific field for a given filing."""
        if field not in self._UPDATABLE_COLS and field != "id":
            raise ValueError(f"Unknown column: {field}")

        col_name = f'"{field}"' if field.isupper() else field
        stmt = text(f"SELECT {col_name} FROM {self.TABLE} WHERE id = :id;")
        with self.engine.connect() as conn:
            return conn.execute(stmt, {"id": id}).scalar_one_or_none()

    def upsert_classification(self, filing_id: str, version: str, **kwargs) -> None:
        """
        Upserts classification results for a filing into nps_classification_results.
        Only fields present in the table are allowed.
        """
        allowed_cols = {
            "KPI_CURRENT_VALUE", "KPI_TREND", "KPI_HISTORICAL_COMPARISON",
            "BENCHMARK_COMPARISON_POSITIVE", "BENCHMARK_COMPARISON_NEGATIVE", "NPS_GOAL_REACHED",
            "TARGET_OUTLOOK", "MGMT_COMPENSATION_GOVERNANCE", "CUSTOMER_CASE_EVIDENCE",
            "NPS_SERVICE_PROVIDER", "METHODOLOGY_DEFINITION", "QUALITATIVE_ONLY", "OTHER",
            "has_numeric_nps", "nps_value_fix", "nps_competition_industry",
            "nps_value_over", "nps_value_below", "nps_goal_value", "nps_goal_change"
        }
        
        # Filter kwargs to only allowed columns
        filtered_kwargs = {k: v for k, v in kwargs.items() if k in allowed_cols}
        
        col_names = ["filing_id", "experiment_version"]
        placeholders = [":filing_id", ":experiment_version"]
        params = {"filing_id": filing_id, "experiment_version": version}
        
        for k, v in filtered_kwargs.items():
            if k.isupper():
                col_names.append(f'"{k}"')
            else:
                col_names.append(k)
            placeholders.append(f":{k}")
            params[k] = v
            
        update_clauses = []
        for k in filtered_kwargs:
            if k.isupper():
                update_clauses.append(f'"{k}" = EXCLUDED."{k}"')
            else:
                update_clauses.append(f'{k} = EXCLUDED.{k}')
        update_clauses.append("classified_at = now()")
        
        cols_str = ", ".join(col_names)
        vals_str = ", ".join(placeholders)
        update_str = ", ".join(update_clauses)
        
        stmt = text(f"""
        INSERT INTO {self.TABLE}_classifications ({cols_str})
        VALUES ({vals_str})
        ON CONFLICT (filing_id, experiment_version) DO UPDATE
        SET {update_str};
        """)
        
        with self.engine.begin() as conn:
            conn.execute(stmt, params)

    def get_classifications(self, filing_id: str) -> list[dict]:
        """
        Retrieves all classification results for a given filing.
        """
        stmt = text(f"SELECT * FROM {self.TABLE}_classifications WHERE filing_id = :filing_id;")
        with self.engine.connect() as conn:
            rows = conn.execute(stmt, {"filing_id": filing_id}).mappings().all()
            return [dict(row) for row in rows]
