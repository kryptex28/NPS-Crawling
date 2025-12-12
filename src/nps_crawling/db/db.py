import psycopg2
import psycopg2.extras
import json
from typing import Any, Optional

class CrawlerDB:
    def __init__(self, dsn: str):
        self.dsn = dsn
        self._conn: Optional[psycopg2.extensions.connection] = None

    def connect(self) -> None:
        if self._conn is None:
            self._conn = psycopg2.connect(self.dsn)
            self._conn.autocommit = False

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    def blacklist_url(self, url: str, *, has_nps: bool = False, content_hash: str | None = None, meta: dict[str, Any] | None = None) -> None:
        self._ensure_conn()
        meta = meta or {}
        sql = """
        INSERT INTO crawled_url (url, blacklisted, has_nps, content_hash, meta)
        VALUES (%s, TRUE, %s, %s, %s::jsonb)
        ON CONFLICT (url) DO UPDATE
        SET
          last_seen_at = now(),
          blacklisted  = TRUE,
          has_nps   = EXCLUDED.has_nps OR crawled_url.has_nps,
          content_hash = COALESCE(EXCLUDED.content_hash, crawled_url.content_hash),
          meta         = crawled_url.meta || EXCLUDED.meta;
        """
        with self._conn.cursor() as cur:
            cur.execute(sql, (url, has_nps, content_hash, json.dumps(meta)))
        self._conn.commit()

    def delete_url(self, url: str) -> bool:
        self._ensure_conn()
        with self._conn.cursor() as cur:
            cur.execute("DELETE FROM crawled_url WHERE url=%s;", (url,))
            deleted = cur.rowcount > 0
        self._conn.commit()
        return deleted

    def is_blacklisted(self, url: str) -> bool:
        self._ensure_conn()
        with self._conn.cursor() as cur:
            cur.execute("SELECT blacklisted FROM crawled_url WHERE url=%s;", (url,))
            row = cur.fetchone()
        return bool(row[0]) if row else False

    def _ensure_conn(self) -> None:
        if self._conn is None:
            raise RuntimeError("DB not connected. Call connect() first.")

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc, tb):
        if self._conn is not None and exc is not None:
            self._conn.rollback()
        self.close()
