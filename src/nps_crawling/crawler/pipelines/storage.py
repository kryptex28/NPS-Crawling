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

import json

from nps_crawling.config import Config


class SaveToJSONPipeline(Config):
    """Pipeline to save items to a JSONL file."""
    def __init__(self):
        """Initialize the pipeline."""
        self.json_path = Config.RAW_JSON_PATH_CRAWLER / Config.RAW_JSON_FILE_CRAWLER

    def open_spider(self, spider):
        """Initialize file handles and paths."""
        self.file = open(self.json_path, 'w', encoding='utf-8')

    def process_item(self, item, spider):
        """Write item to JSONL file."""
        # TODO: save as parquet instead of jsonl here somewhere probably
        line = json.dumps(dict(item), ensure_ascii=False)
        self.file.write(line + "\n")
        return item

    def close_spider(self, spider):
        """Finalize file."""
        self.file.close()
