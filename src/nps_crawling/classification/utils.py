"""Classification pipeline to process and classify company data."""

import logging

from nps_crawling.classification.data_processing.preprocess_data import ClassificationDataProcessing
from nps_crawling.classification.model.classification import ClassificationModelPipeline
from nps_crawling.config import Config

logger = logging.getLogger(__name__)


class ClassificationPipeline(Config):
    """Classification pipeline class."""

    def __init__(self):
        """Initialize the ClassificationPipeline."""
        self.get_data = ClassificationDataProcessing()
        self.model_pipeline = ClassificationModelPipeline()

    def classification_workflow(self):
        """Classification workflow method."""
        logger.info("Starting classification")

        json_files = self.get_data.get_all_json_files()
        total_files = len(json_files)
        logger.info(f"Number of files to classify: {total_files}")

        for i, json_file in enumerate(json_files, start=1):
            logger.info(f"[{i}/{total_files}] Processing {json_file.name}")
            records = self.get_data.load_file(json_file)
            self.model_pipeline.model_workflow(
                records,
                source_filename=json_file.stem,
            )
            logger.info(f"[{i}/{total_files}] Finished {json_file.name}")

        logger.info("Finished classification")
        return None