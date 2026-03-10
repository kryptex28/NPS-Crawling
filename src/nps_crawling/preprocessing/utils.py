"""Pre-processing pipeline to clean, filter, and store data."""

import json
import logging

from nps_crawling.config import Config

from .cleaning import CleanTextPipeline
from .filtering import NpsMentionFilterPipeline
from .storage import SaveToJSONPipeline

logger = logging.getLogger(__name__)


class PreProcessingPipeline(Config):
    """Pre-processing pipeline class to clean, filter, and store data.

    This pipeline reads JSON files from json_raw/, runs cleaning and NPS-mention
    filtering, and writes one output JSON per input file to json_processed/.
    Each output record contains all original data plus a "context" list.
    """
    def __init__(self):
        """Initialize the PreProcessingPipeline."""
        self.json_raw_dir = Config.RAW_JSON_PATH_CRAWLER

        self.cleaner = CleanTextPipeline()
        self.filter = NpsMentionFilterPipeline()
        self.storage = SaveToJSONPipeline()

    def pre_processing_workflow(self):
        """Workflow method to pre process data.

        For each JSON file in json_raw/:
            1. Load the list of records.
            2. Clean core_text (HTML → plain text).
            3. Extract context windows from core_text.
            4. Write the enriched records to json_processed/<same filename>.
        """
        json_files = sorted(self.json_raw_dir.glob("*.json"))
        if not json_files:
            logger.info("No raw JSON files found to process")
            return None

        files_before = self.storage.count_json_files()
        processed_count = 0

        for json_file in json_files:
            with open(json_file, "r", encoding="utf-8") as f:
                records = json.load(f)

            if not records:
                continue

            records = self.cleaner.cleaning_workflow(records)
            records = self.filter.filtering_workflow(records)
            self.storage.storage_workflow(records, source_filename=json_file.stem)

            processed_count += len(records)
            logger.info(f"Processed {json_file.name} ({len(records)} records)")

        files_after = self.storage.count_json_files()
        logger.info(f"Finished pre-processing. Total records processed: {processed_count}")
        logger.info(f"New JSON files created: {files_after - files_before}")

        return None
