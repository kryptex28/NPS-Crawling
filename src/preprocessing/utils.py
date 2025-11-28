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
        process the filings (stored in JSONL) in batch sizes as defined 
        in Config var FILINGS_PASSED_THROUGH_PROCESS_AT_ONCE
        """
        logger.info(f"Starting pre-processing raw data in batch sizes of {self.files_at_once}")

        files_before = self.storage.count_parquet_files()

        batch = []
        batch_size = self.files_at_once
        processed_count = 0

        # TODO: --> edit 27.11.25: these will be parquet files in the future, no more json
        # (so raw parquet files will be loaded here)
        with self.raw_json_file_crawler.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue

                filing = json.loads(line)
                batch.append(filing)

                if len(batch) >= batch_size:
                    cleaned_dict_batch = self.cleaner.cleaning_workflow(batch)
                    context_windows_dict_batch = self.filter.filtering_workflow(cleaned_dict_batch)
                    self.storage.storage_workflow(context_windows_dict_batch)

                    processed_count += len(batch)
                    logger.info(f"Processed {processed_count} filings")
                    batch = [] 

        # last batch leftovers
        if batch:
            cleaned_dict_batch = self.cleaner.cleaning_workflow(batch)
            context_windows_dict_batch = self.filter.filtering_workflow(cleaned_dict_batch)
            self.storage.storage_workflow(context_windows_dict_batch)

            processed_count += len(batch)

        files_after = self.storage.count_parquet_files()

        logger.info(f"Finished pre-processing data. Total filings processed: {processed_count}")
        logger.info(f"New parquet files created: {files_after - files_before}")

        return None