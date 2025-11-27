from src.config import Config

import json

from .cleaning import CleanTextPipeline
from .filtering import NpsMentionFilterPipeline
from .storage import SaveToJSONPipeline

import logging
logger = logging.getLogger(__name__)

class PreProcessingPipeline(Config):

    def __init__(self):

        self.files_at_once = Config.FILINGS_PASSED_THROUGH_PROCESS_AT_ONCE
        self.raw_json_file_crawler_name = Config.RAW_JSON_FILE_CRAWLER
        self.raw_json_file_crawler = Config.RAW_JSON_PATH_CRAWLER / self.raw_json_file_crawler_name

        self.cleaner = CleanTextPipeline()
        self.filter = NpsMentionFilterPipeline()
        self.storage = SaveToJSONPipeline()

    #TODO: logic here needs to be adapted later on. we don't want to run over all stored 
    # filings everytime, just the ones that are new
    # --> edit 27.11.25: only pre-process the parquet files, that are not marked in database
    # as pre-processed yet (need to implement that logic first though)
    def pre_processing_workflow(self):
        """
        workflow method to pre process data. cleaning --> filtering --> storaging.
        process the filings (stored in JSON) in batch sizes as defined 
        in Config var FILINGS_PASSED_THROUGH_PROCESS_AT_ONCE
        """
        logger.info("Starting pre-processing raw data")

        # TODO: --> edit 27.11.25: these will be parquet files in the future, no more json
        # (so raw parquet files will be loaded here)
        filings = []
        with self.raw_json_file_crawler.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                filings.append(json.loads(line))

        total = len(filings)
        logger.info(f"Processing {total} filings in batch size of: {self.files_at_once}")

        files_before = self.storage.count_parquet_files()

        for start in range(0, total, self.files_at_once):
            end = start + self.files_at_once
            dict_batch = filings[start:end]

            cleaned_dict_batch = self.cleaner.cleaning_workflow(dict_batch)
            context_windows_dict_batch = self.filter.filtering_workflow(cleaned_dict_batch)
            self.storage.storage_workflow(context_windows_dict_batch)

        files_after = self.storage.count_parquet_files()

        logger.info(f"New parquet files created: {files_after - files_before}")
        logger.info(f"Finished pre-processing data")

        return None
    