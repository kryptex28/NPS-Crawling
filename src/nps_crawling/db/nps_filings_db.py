# nps_filings.py
from __future__ import annotations

# Used to serialize Python dicts into JSON strings for JSONB parameters.
import json

# Types for metadata dicts and for restricting meta_mode to allowed strings.
from typing import Any, Literal

# Engine is the database entry point; text() creates parameterized SQL strings.
from sqlalchemy import Engine, text


class NpsFilingsDB:
    # Name of the target PostgreSQL table.
    TABLE = "nps_filings"

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
        "has_nps",
        "meta",
        "path_raw",
        "path_cleaned",
        "path_prepro",
    }

    def __init__(self, engine: Engine):
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
        has_nps: bool = False,
        meta: dict[str, Any] | None = None,
        path_raw: str | None = None,
        path_cleaned: str | None = None,
        path_prepro: str | None = None,
        meta_mode: Literal["merge", "replace"] = "merge",
    ) -> None:
        # Ensure meta is always a dict so it can be serialized and stored in JSONB.
        meta = meta or {}

        # Choose whether meta is merged with existing JSONB (||) or replaced entirely.
        meta_update = (
            f"{self.TABLE}.meta || EXCLUDED.meta"
            if meta_mode == "merge"
            else "EXCLUDED.meta"
        )

        # Insert a new filing; on id conflict update selected fields.
        # Arrays: CAST is used to avoid issues with typed parameters in SQLAlchemy text().
        # COALESCE(..., ARRAY[]::text[]) ensures NOT NULL array columns get an empty array if None is passed.
        stmt = text(f"""
        INSERT INTO {self.TABLE} (
          id, ciks, period_ending, display_names, root_forms, file_date, form, adsh,
          file_type, file_description, film_num, keywords,
          blacklisted, has_nps, meta, path_raw, path_cleaned, path_prepro
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
          COALESCE(CAST(:keywords AS text[]), CAST(ARRAY[] AS text[])),
          :blacklisted, :has_nps, CAST(:meta AS jsonb),
          :path_raw, :path_cleaned, :path_prepro
        )
        ON CONFLICT (id) DO UPDATE
        SET
          -- Update crawl timestamp on every upsert conflict.
          last_crawled     = now(),
          -- "Sticky" booleans: once TRUE, remain TRUE.
          blacklisted      = {self.TABLE}.blacklisted OR EXCLUDED.blacklisted,
          has_nps          = {self.TABLE}.has_nps OR EXCLUDED.has_nps,
          -- Meta can be merged or replaced depending on meta_mode.
          meta             = {meta_update},

          -- Only overwrite paths when a new non-NULL value is provided.
          path_raw         = COALESCE(EXCLUDED.path_raw, {self.TABLE}.path_raw),
          path_cleaned     = COALESCE(EXCLUDED.path_cleaned, {self.TABLE}.path_cleaned),
          path_prepro      = COALESCE(EXCLUDED.path_prepro, {self.TABLE}.path_prepro),

          -- Arrays: only overwrite when the corresponding parameter is not NULL.
          ciks             = CASE WHEN :ciks IS NULL THEN {self.TABLE}.ciks ELSE EXCLUDED.ciks END,
          display_names    = CASE WHEN :display_names IS NULL THEN {self.TABLE}.display_names ELSE EXCLUDED.display_names END,
          root_forms       = CASE WHEN :root_forms IS NULL THEN {self.TABLE}.root_forms ELSE EXCLUDED.root_forms END,
          film_num         = CASE WHEN :film_num IS NULL THEN {self.TABLE}.film_num ELSE EXCLUDED.film_num END,
          keywords         = CASE WHEN :keywords IS NULL THEN {self.TABLE}.keywords ELSE EXCLUDED.keywords END,

          -- For scalar fields, keep existing values if the new value is NULL.
          period_ending    = COALESCE(EXCLUDED.period_ending, {self.TABLE}.period_ending),
          file_date        = COALESCE(EXCLUDED.file_date, {self.TABLE}.file_date),
          form             = COALESCE(EXCLUDED.form, {self.TABLE}.form),
          adsh             = COALESCE(EXCLUDED.adsh, {self.TABLE}.adsh),
          file_type        = COALESCE(EXCLUDED.file_type, {self.TABLE}.file_type),
          file_description = COALESCE(EXCLUDED.file_description, {self.TABLE}.file_description);
        """)

        # Use a transaction (engine.begin) so the statement is committed automatically on success.
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
                    "has_nps": has_nps,
                    "meta": json.dumps(meta),
                    "path_raw": path_raw,
                    "path_cleaned": path_cleaned,
                    "path_prepro": path_prepro,
                },
            )

    def update_fields(
        self,
        id: str,
        *,
        touch_last_crawled: bool = True,
        meta_mode: Literal["merge", "replace"] = "replace",
        **fields: Any,
    ) -> int:
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
            # Meta is stored as JSONB and can be merged or replaced.
            if col == "meta":
                val = {} if val is None else val
                params["meta"] = json.dumps(val)
                if meta_mode == "merge":
                    set_parts.append(f"meta = {self.TABLE}.meta || CAST(:meta AS jsonb)")
                else:
                    set_parts.append("meta = CAST(:meta AS jsonb)")
                continue

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
                set_parts.append(f"{col} = NULL")
            else:
                params[col] = val
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
        # Delete by primary key and return whether any row was removed.
        stmt = text(f"DELETE FROM {self.TABLE} WHERE id = :id;")
        with self.engine.begin() as conn:
            res = conn.execute(stmt, {"id": id})
            return (res.rowcount or 0) > 0

    def is_blacklisted(self, id: str) -> bool:
        # Read the blacklisted flag; return False if the row does not exist.
        stmt = text(f"SELECT blacklisted FROM {self.TABLE} WHERE id = :id;")
        with self.engine.connect() as conn:
            val = conn.execute(stmt, {"id": id}).scalar_one_or_none()
            return bool(val) if val is not None else False

    def has_nps(self, id: str) -> bool:
        # Read the has_nps flag; return False if the row does not exist.
        stmt = text(f"SELECT has_nps FROM {self.TABLE} WHERE id = :id;")
        with self.engine.connect() as conn:
            val = conn.execute(stmt, {"id": id}).scalar_one_or_none()
            return bool(val) if val is not None else False

    def cleaned_exists(self, id: str) -> bool:
        # True if path_cleaned is set and non-empty; False if row does not exist.
        stmt = text(f"""
        SELECT (path_cleaned IS NOT NULL AND path_cleaned <> '')
        FROM {self.TABLE}
        WHERE id = :id;
        """)
        with self.engine.connect() as conn:
            val = conn.execute(stmt, {"id": id}).scalar_one_or_none()
            return bool(val) if val is not None else False

    def preprocessed_exists(self, id: str) -> bool:
        # True if path_prepro is set and non-empty; False if row does not exist.
        stmt = text(f"""
        SELECT (path_prepro IS NOT NULL AND path_prepro <> '')
        FROM {self.TABLE}
        WHERE id = :id;
        """)
        with self.engine.connect() as conn:
            val = conn.execute(stmt, {"id": id}).scalar_one_or_none()
            return bool(val) if val is not None else False

    def blacklist(self, id: str) -> None:
        # Mark a filing as blacklisted; creates the row if it does not exist.
        stmt = text(f"""
        INSERT INTO {self.TABLE} (id, blacklisted)
        VALUES (:id, TRUE)
        ON CONFLICT (id) DO UPDATE
        SET blacklisted = TRUE, last_crawled = now();
        """)
        with self.engine.begin() as conn:
            conn.execute(stmt, {"id": id})

    def add_keyword(self, id: str, kw: str) -> bool:
        # Add a keyword only if it is not already present.
        # If the row does not exist, create it with keywords = [kw].
        # Returns True if a keyword was added or the row was inserted; otherwise False.
        stmt = text(f"""
        WITH updated AS (
          UPDATE {self.TABLE}
          SET
            keywords = array_append(keywords, :kw),
            last_crawled = now()
          WHERE id = :id
            AND NOT (:kw = ANY(keywords))
          RETURNING 1
        ),
        inserted AS (
          INSERT INTO {self.TABLE} (id, keywords)
          SELECT :id, CAST(ARRAY[:kw] AS text[])
          WHERE NOT EXISTS (SELECT 1 FROM {self.TABLE} WHERE id = :id)
          RETURNING 1
        )
        SELECT EXISTS (
          SELECT 1 FROM updated
          UNION ALL
          SELECT 1 FROM inserted
        ) AS added;
        """)
        with self.engine.begin() as conn:
            return bool(conn.execute(stmt, {"id": id, "kw": kw}).scalar_one())
