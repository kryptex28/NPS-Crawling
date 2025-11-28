"""Pipelines for storing crawled data."""

import json
from pathlib import Path

from nps_crawling.preprocessing.json_to_parquet import json_input_to_parquet


class SaveToJSONPipeline:
    """Pipeline to save items to a JSON file and convert to Parquet."""

    def __init__(self):
        """Initialize the pipeline."""
        self.json_path = Path('')
        self.parquet_path = Path('')

    def open_spider(self, spider):
        """Initialize file handles and paths."""
        self.file = open('nps_filings.json', 'w')
        self.file.write('[')

    def close_spider(self, spider):
        """Finalize file and convert to Parquet."""
        self.file.write(']')
        self.file.close()

        # Convert JSON to Parquet
        json_input_to_parquet(self.json_path, self.parquet_path)

    def process_item(self, item, spider):
        """Write item to JSON file."""
        line = json.dumps(dict(item)) + ",\n"
        self.file.write(line)
        return item
