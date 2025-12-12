__author__ = "David Schaetz"
from db import CrawlerDB

DSN = "postgresql://crawler:crawler@localhost:5432/crawler"

with CrawlerDB(DSN) as db:
    db.blacklist_url("https://example.com/doc.pdf", has_nps=True)
    print(db.is_blacklisted("https://example.com/doc.pdf"))  # True
    print(db.delete_url("https://example.com/doc.pdf"))      # True
    print(db.is_blacklisted("https://example.com/doc.pdf"))  # False
