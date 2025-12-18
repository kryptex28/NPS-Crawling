CREATE TABLE IF NOT EXISTS crawled_url (
  id              BIGSERIAL PRIMARY KEY,
  url             TEXT NOT NULL UNIQUE,
  first_seen_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  last_seen_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  blacklisted     BOOLEAN NOT NULL DEFAULT FALSE,
  has_nps         BOOLEAN NOT NULL DEFAULT FALSE,
  content_hash    TEXT NULL,
  meta            JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_crawled_url_blacklisted ON crawled_url (blacklisted);
CREATE INDEX IF NOT EXISTS idx_crawled_url_last_seen   ON crawled_url (last_seen_at);
CREATE INDEX IF NOT EXISTS idx_crawled_url_has_nps     ON crawled_url (has_nps);
