import json
from pathlib import Path
from preprocessing.json_to_parquet import json_input_to_parquet

class SaveToJSONPipeline:
    def open_spider(self, spider):
        self.file = open('nps_filings.json', 'w')
        self.file.write('[')

    def close_spider(self, spider):
        self.file.write(']')
        self.file.close()

        # Convert JSON to Parquet
        json_input_to_parquet(self.json_path, self.parquet_path)

    def process_item(self, item, spider):
        line = json.dumps(dict(item)) + ",\n"
        self.file.write(line)
        return item
