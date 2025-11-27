# import json
# from pathlib import Path
# from preprocessing.json_to_parquet import json_input_to_parquet

# class SaveToJSONPipeline:
#     def open_spider(self, spider):
#         self.file = open('nps_filings.json', 'w')
#         self.file.write('[')

#     def close_spider(self, spider):
#         self.file.write(']')
#         self.file.close()

#         # Convert JSON to Parquet
#         json_input_to_parquet(self.json_path, self.parquet_path)

#     def process_item(self, item, spider):
#         line = json.dumps(dict(item)) + ",\n"
#         self.file.write(line)
#         return item



# JSONL avoids the JSON formatting issue we had downstream.
# data will be converted to parquet files later anyways
import json
from src.config import Config

class SaveToJSONPipeline(Config):

    def __init__(self):
        
        self.json_path = Config.RAW_JSON_PATH_CRAWLER / Config.RAW_JSON_FILE_CRAWLER

    def open_spider(self, spider):

        self.file = open(self.json_path, 'w', encoding='utf-8')

    def process_item(self, item, spider):
        
        #TODO: save as parquet instead of jsonl here somewhere probably
        line = json.dumps(dict(item), ensure_ascii=False)
        self.file.write(line + "\n")
        return item

    def close_spider(self, spider):
       
        self.file.close()
