"""Pipelines for storing crawled data."""
import json
from datetime import datetime
from uuid import uuid4

from nps_crawling.config import Config


class SaveToJSONPipeline(Config):
    """Collect scraped items during a crawl and persist them as JSON files.

    Each record is written as a JSON file with two top-level keys:
    - ``metadata``: all filing fields except ``core_text``
    - ``core_text``: the extracted text content of the filing
    """

    def __init__(self):
        """Initialize pipeline state."""
        self.json_root = Config.RAW_JSON_PATH_CRAWLER
        self.records = []
        self.flush_every = 1

    def open_spider(self, spider):
        """Reset the in-memory buffer when the spider starts."""
        self.records = []

    def _to_serializable(self, val):
        """Recursively convert a value to a JSON-serializable type."""
        if isinstance(val, (str, int, float, bool, type(None))):
            return val
        if isinstance(val, list):
            return [self._to_serializable(x) for x in val]
        if hasattr(val, "__dict__"):
            return {
                k: self._to_serializable(v)
                for k, v in vars(val).items()
                if not k.startswith("_")
            }
        return str(val)

    def process_item(self, item, spider):
        """Buffer a single scraped item and flush when the buffer is full."""
        record = dict(item)

        core_text = self._to_serializable(record.pop("core_text", None))

        metadata = {k: self._to_serializable(v) for k, v in record.items()}

        self.records.append({"metadata": metadata, "core_text": core_text})

        if len(self.records) >= self.flush_every:
            self._flush_buffer()
        return item

    def close_spider(self, spider):
        """Flush any remaining records when the spider closes."""
        if self.records:
            self._flush_buffer()

    def _flush_buffer(self):
        if not self.records:
            return

        ts = datetime.utcnow().strftime("%Y%m%dT%H%M%S")
        fname = f"chunk_{ts}_{uuid4().hex}.json"

        #TODO: David - raw json saving
        with open(self.json_root / fname, "w", encoding="utf-8") as f:
            json.dump(self.records, f, ensure_ascii=False, indent=2)

        self.records = []
