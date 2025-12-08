"""Pre-processing pipeline to clean, filter, and store data."""

import logging

import pandas as pd

from nps_crawling.config import Config

from .cleaning import CleanTextPipeline
from .filtering import NpsMentionFilterPipeline
from .storage import SaveToJSONPipeline

logger = logging.getLogger(__name__)


class PreProcessingPipeline(Config):
    """Pre-processing pipeline class to clean, filter, and store data.

    This pipeline coordinates text cleaning, NPS-mention filtering and
    storage of processed results.
    """
    def __init__(self):
        """Initialize the PreProcessingPipeline."""
        self.files_at_once = Config.FILINGS_PASSED_THROUGH_PROCESS_AT_ONCE
        self.raw_parquet_dir_crawler = Config.RAW_PARQUET_PATH_CRAWLER

        self.cleaner = CleanTextPipeline()
        self.filter = NpsMentionFilterPipeline()
        self.storage = SaveToJSONPipeline()

    # TODO: logic here needs to be adapted later on. we don't want to run over all stored
    # filings everytime, just the ones that are new
    # --> edit 27.11.25: only pre-process the parquet files, that are not marked in database
    # as pre-processed yet (need to implement that logic first though)
    def pre_processing_workflow(self):
        """Workflow method to pre process data.

        Cleaning --> filtering --> storaging. Processes the filings (stored in
        Parquet) in batch sizes as defined in the Config variable
        FILINGS_PASSED_THROUGH_PROCESS_AT_ONCE.
        """
        logger.info(f"Starting pre-processing raw data in batch sizes of {self.files_at_once}")

        files_before = self.storage.count_parquet_files()

        batch = []
        batch_size = self.files_at_once
        processed_count = 0

        parquet_files = sorted(self.raw_parquet_dir_crawler.glob("*.parquet"))
        if not parquet_files:
            logger.info("No raw filings found to process")
            return None

        for parquet_file in parquet_files:
            df = pd.read_parquet(parquet_file)
            if df.empty:
                continue

            for filing in df.to_dict(orient="records"):
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
