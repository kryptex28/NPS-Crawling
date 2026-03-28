"""Classification pipeline to process and classify company data."""

import json
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

        total_windows_classified = 0

        for i, json_file in enumerate(json_files, start=1):
            logger.info(f"[{i}/{total_files}] Processing {json_file.name}")
            records = self.get_data.load_file(json_file)

            total_windows_classified += sum(len(record.get("context", [])) for record in records)

            self.model_pipeline.model_workflow(
                records,
                source_filename=json_file.stem,
            )
            logger.info(f"[{i}/{total_files}] Finished {json_file.name}")

        # Generate summary report
        summary = {
            "experiment_setup": {
                "classification_version": self.CLASSIFICATION_VERSION,
                "preprocessing_version": self.PREPROCESSING_VERSION,
                "classification_model": self.MODEL,
                "ollama_persona": self.OLLAMA_PERSONA if self.MODEL == "Ollama" else None,
            },
            "statistics": {
                "total_files_classified": total_files,
                "total_windows_classified": total_windows_classified,
            },
        }

        summary_path = self.NPS_CLASSIFIED_JSON / f"classification_{self.CLASSIFICATION_VERSION}.json"
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)

        logger.info(f"Classification report saved to {summary_path}")
        logger.info("Finished classification")
        return None
