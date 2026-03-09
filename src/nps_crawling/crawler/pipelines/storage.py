"""Pipelines for storing crawled data."""

# import json
# from pathlib import Path
#
# from nps_crawling.preprocessing.json_to_parquet import json_input_to_parquet
#
#
# class SaveToJSONPipeline:
#    """Pipeline to save items to a JSON file and convert to Parquet."""
#
#    def __init__(self):
#        """Initialize the pipeline."""
#        self.json_path = Path('')
#        self.parquet_path = Path('')
#
#    def open_spider(self, spider):
#        """Initialize file handles and paths."""
#        self.file = open('nps_filings.json', 'w')
#        self.file.write('[')
#
#    def close_spider(self, spider):
#        """Finalize file and convert to Parquet."""
#        self.file.write(']')
#        self.file.close()
#
#        # Convert JSON to Parquet
#        json_input_to_parquet(self.json_path, self.parquet_path)
#
#    def process_item(self, item, spider):
#        """Write item to JSON file."""
#        line = json.dumps(dict(item)) + ",\n"
#        self.file.write(line)
#        return item
#

from datetime import datetime
from uuid import uuid4

import pandas as pd
import pyarrow as pa

from nps_crawling.config import Config

# Remark: for backup reasons - not needed anymore due to storing into parquet Files
"""class SaveToJSONPipeline(Config):
    # Pipeline to save items to a JSONL file.
    def __init__(self):
        # Initialize the pipeline.
        self.json_path = Config.RAW_JSON_PATH_CRAWLER / Config.RAW_JSON_FILE_CRAWLER

    def open_spider(self, spider):
        # Initialize file handles and paths.
        self.file = open(self.json_path, 'w', encoding='utf-8')

    def process_item(self, item, spider):
        # Write item to JSONL file.
        # TODO: save as parquet instead of jsonl here somewhere probably
        line = json.dumps(dict(item), ensure_ascii=False)
        self.file.write(line + "\n")
        return item

    def close_spider(self, spider):
        # Finalize file.
        self.file.close() """


class SaveToParquetPipeline(Config):
    """Collect scraped items during a crawl and persist them as Parquet chunks.

    This writes multiple files under RAW_PARQUET_PATH_CRAWLER so data is
    persisted incrementally.
    """

    def __init__(self):
        """Initialize pipeline state.

        Attributes:
            parquet_root (Path): Directory where parquet chunks are written.
            records (list): In-memory buffer of records to flush.
            flush_every (int): Number of records to collect before flushing.
        """
        self.parquet_root = Config.RAW_PARQUET_PATH_CRAWLER
        self.records = []
        self.flush_every = 1

    def open_spider(self, spider):
        """Called when the spider is opened.

        Resets the in-memory buffer to start collecting records for a new
        crawl run.
        """
        # reset buffer when a spider starts
        self.records = []

    def _to_serializable(self, val):
        """Convert a value to a PyArrow-serializable type."""
        if isinstance(val, (str, int, float, bool, type(None))):
            return val
        if isinstance(val, list):
            return "; ".join(str(x) for x in val) if val else ""
        if hasattr(val, "__dict__"):
            # Flatten custom objects (e.g. Filing) to dict of strings
            out = {}
            for k, v in vars(val).items():
                if k.startswith("_"):
                    continue
                out[k] = self._to_serializable(v)
            return out
        return str(val)

    def _record_to_serializable(self, record):
        """Convert record so all values are PyArrow-serializable."""
        result = {}
        for k, v in record.items():
            if hasattr(v, "__dict__") and not isinstance(v, (str, int, float, bool, type(None))):
                # Flatten object into top-level keys
                for attr, val in vars(v).items():
                    if attr.startswith("_"):
                        continue
                    key = f"{k}_{attr}"
                    result[key] = self._to_serializable(val)
            else:
                result[k] = self._to_serializable(v)
        return result

    def process_item(self, item, spider):
        """Process and buffer a single scraped item.

        Flattens list fields that would otherwise create nested types in
        Parquet, appends the record to the buffer and flushes the buffer to
        disk when it reaches the configured size.

        Args:
            item (scrapy.Item or dict): Scraped item to persist.
            spider: The spider instance (unused).

        Returns:
            The original item (unchanged).
        """
        record = dict(item)
        keywords = record.get("keywords_found")
        if isinstance(keywords, list):
            record["keywords_found"] = "; ".join(keywords)

        self.records.append(self._record_to_serializable(record))

        if len(self.records) >= self.flush_every:
            self._flush_buffer()
        return item

    def close_spider(self, spider):
        """Flush any remaining records when the spider closes.

        If the buffer is empty this is a no-op.
        """
        if not self.records:
            return

        self._flush_buffer()

    def _flush_buffer(self):
        if not self.records:
            return

        table = pa.Table.from_pylist(self.records)

        # view the table schema for debugging here if needed
        df = table.to_pandas()  

        ts = datetime.utcnow().strftime("%Y%m%dT%H%M%S")
        fname = f"chunk_{ts}_{uuid4().hex}.parquet"
        
        # gets saved with every meta information dynamically received from crawler
        df.to_parquet(self.parquet_root / fname, compression="snappy", index=False)

        # clear buffer after flush
        self.records = []
