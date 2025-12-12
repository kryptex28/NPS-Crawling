"""Minimal example for using the CrawlerDB wrapper.

What this script does:
  1) Connects to the PostgreSQL database via DSN.
  2) Blacklists a URL.
  3) Checks blacklist status for two URLs and prints the results.

Requirements:
  - PostgreSQL is running and reachable at the DSN below.
  - Table `public.crawled_url` exists.

Notes:
  - `delete_url()` is commented out. If you uncomment it, the final blacklist check
    should return False because the row will be deleted.
"""

__author__ = "David Schaetz"

from db import CrawlerDB

DSN = "postgresql://crawler:crawler@localhost:5432/crawler"

with CrawlerDB(DSN) as db:
    # Insert/update and mark this URL as blacklisted.
    db.blacklist_url("https://example.com/doc.pdf", has_nps=True)

    # Check whether URLs are blacklisted.
    print(db.is_blacklisted("https://example.com/doc.pdf"))   # True
    print(db.is_blacklisted("https://example.com/test.pdf"))  # True (if previously inserted)

    # Uncomment to delete the entry:
    print(db.delete_url("https://example.com/doc.pdf"))      # True if row existed

    # If you deleted the URL above, this would print False. Otherwise it will still be True.
    print(db.is_blacklisted("https://example.com/doc.pdf"))   # False if deleted, else True
