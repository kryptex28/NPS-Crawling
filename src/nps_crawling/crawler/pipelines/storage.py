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

import pyarrow as pa
import pyarrow.parquet as pq

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


def _value_to_str(val) -> str:
    """Convert a value to a string for Parquet; lists become semicolon-joined."""
    if val is None:
        return ""
    if isinstance(val, list):
        return "; ".join(str(v) for v in val) if val else ""
    return str(val)


def _flatten_filing(filing) -> dict:
    """Turn a Filing object into a flat dict of strings by reflecting over its attributes.

    Any attribute on the Filing instance is included; no need to update this when
    the Filing model gains or loses fields. Private names (e.g. _id) become filing_id.
    """
    out = {}
    for key, val in vars(filing).items():
        name = key.lstrip("_")
        out[f"filing_{name}"] = _value_to_str(val)
    return out


class SaveToParquetPipeline(Config):
    """Save each crawled item as one raw Parquet file (BetterSpider: filing + core_text + keyword).

    No fixed schema: all Filing fields are flattened to strings and written
    with whatever the item contains. One Parquet file per crawled document.
    """

    def __init__(self):
        """Initialize pipeline state."""
        self.parquet_root = Config.RAW_PARQUET_PATH_CRAWLER
        self.records = []
        self.flush_every = 1

    def open_spider(self, spider):
        """Reset buffer when the spider starts."""
        self.records = []

    def process_item(self, item, spider):
        """Buffer one item and write one Parquet file per item (raw, schema inferred)."""
        record = self._item_to_raw_record(item)
        if record is None:
            return item
        self.records.append(record)
        if len(self.records) >= self.flush_every:
            self._flush_buffer()
        return item

    def _item_to_raw_record(self, item) -> dict | None:
        """Build a single raw record from BetterSpider item: flattened filing + core_text + keyword."""
        item = dict(item)
        if "filing" not in item:
            return None
        filing = item["filing"]
        record = _flatten_filing(filing)
        record["core_text"] = item.get("core_text") or ""
        record["keyword"] = item.get("keyword") or ""
        return record

    def close_spider(self, spider):
        """Flush any remaining records when the spider closes."""
        if not self.records:
            return
        self._flush_buffer()

    def _flush_buffer(self):
        if not self.records:
            return
        # No fixed schema: let PyArrow infer from the record(s)
        table = pa.Table.from_pylist(self.records)
        ts = datetime.utcnow().strftime("%Y%m%dT%H%M%S")
        fname = f"chunk_{ts}_{uuid4().hex}.parquet"
        pq.write_table(table, self.parquet_root / fname, compression="snappy")
        self.records = []
