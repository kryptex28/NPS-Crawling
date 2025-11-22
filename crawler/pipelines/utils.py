from config.config import Config
import json

from .cleaning import CleanTextPipeline
from .filtering import NpsMentionFilterPipeline
from .storage import SaveToJSONPipeline

class PreProcessingPipeline(Config):

    def __init__(self):

        self.files_at_once = Config.FILINGS_PASSED_THROUGH_PROCESS_AT_ONCE
        self.raw_json_file_crawler_name = Config.RAW_JSON_FILE_FROM_CRAWLER
        self.raw_json_file_crawler = Config.RAW_JSON_PATH_CRAWLER / self.raw_json_file_crawler_name

        self.cleaner = CleanTextPipeline()
        self.filter = NpsMentionFilterPipeline()
        self.storage = SaveToJSONPipeline()

    #TODO: logic here needs to be adapted later on. we don't want to run over all stored 
    # filings everytime, just the ones that are new
    def pre_processing_workflow(self):
        """
        workflow method to pre process data. cleaning --> filtering --> storaging.
        process the filings (stored in JSON) in batch sizes as defined 
        in Config var FILINGS_PASSED_THROUGH_PROCESS_AT_ONCE
        """




        #TODO: JSON needs to be in correct format. this should be removed here
        # it's just a quick fix. this code should be used instead:
        # with self.raw_json_file_crawler.open("r", encoding="utf-8") as f:
        #     filings = json.load(f)
        with self.raw_json_file_crawler.open("r", encoding="utf-8") as f:
            raw = f.read()
        if raw.endswith("]"):
            before, _, closing = raw.rpartition("]")
            before = before.rstrip()
            if before.endswith(","):
                before = before[:-1] 
            raw = before + "]"
        filings = json.loads(raw)




        total = len(filings)

        for start in range(0, total, self.files_at_once):
            end = start + self.files_at_once
            dict_batch = filings[start:end]

            cleaned_dict_batch = self.cleaner.cleaning_workflow(dict_batch)
            context_windows_dict_batch = self.filter.filtering_workflow(cleaned_dict_batch)
            self.storage.storage_workflow(context_windows_dict_batch)
        
        return None

    