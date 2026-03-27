"""Pre-processing pipeline to clean, filter, score similarity, and store data."""

import json
import logging

from tqdm import tqdm

from nps_crawling.config import Config

from .cleaning import CleanTextPipeline
from .filtering import NpsMentionFilterPipeline
from .similarity import SimilarityPipeline
from .storage import SaveToJSONPipeline

logger = logging.getLogger(__name__)


class PreProcessingPipeline(Config):
    """Pre-processing pipeline class to clean, filter, and store data.

    Pipeline per file
    -----------------
    1. **Clean** – HTML/XML → plain text.
    2. **Filter** – extract context windows around NPS-related phrases.
    3. **Score** – semantic similarity of each window against a reference text.
    4. **Split** – splits contexts based on threshold.
    5. **Store** – high-scoring contexts go to ``json_processed/``; low-scoring 
       contexts go to ``json_reject/``. Both are saved.
    """
    def __init__(self):
        """Initialize the PreProcessingPipeline."""
        self.json_raw_dir = Config.RAW_JSON_PATH_CRAWLER

        self.cleaner = CleanTextPipeline()
        self.filter = NpsMentionFilterPipeline()
        self.similarity = SimilarityPipeline()
        self.storage = SaveToJSONPipeline()

    def pre_processing_workflow(self):
        """Run the full pre-processing workflow over all raw JSON files."""
        json_files = sorted(self.json_raw_dir.glob("*.json"))
        if not json_files:
            logger.info("No raw JSON files found to process")
            return None

        files_before_processed = self.storage.count_json_files()
        files_before_rejected = self.storage.count_rejected_files()
        processed_count = 0
        accepted_count = 0
        rejected_count = 0

        for json_file in tqdm(json_files, desc="Pre-processing documents", unit="file"):
            with open(json_file, "r", encoding="utf-8") as f:
                records = json.load(f)

            if not records:
                continue

            records = self.cleaner.cleaning_workflow(records)
            records = self.filter.filtering_workflow(records)

            accepted_records, rejected_records = self.similarity.similarity_workflow(records)

            self.storage.storage_workflow(
                accepted_records, source_filename=json_file.stem, reject=False, update_db=True
            )
            self.storage.storage_workflow(
                rejected_records, source_filename=json_file.stem, reject=True, update_db=False
            )
            accepted_count += 1

            processed_count += len(records)
            logger.info("Processed %s (%d records) — SPLIT", json_file.name, len(records))

        files_after_processed = self.storage.count_json_files()
        files_after_rejected = self.storage.count_rejected_files()
        logger.info("Finished pre-processing. Total records processed: %d", processed_count)
        logger.info("Files accepted: %d  |  Files rejected: %d", accepted_count, rejected_count)
        logger.info(
            "New processed files: %d  |  New rejected files: %d",
            files_after_processed - files_before_processed,
            files_after_rejected - files_before_rejected,
        )

        return None
