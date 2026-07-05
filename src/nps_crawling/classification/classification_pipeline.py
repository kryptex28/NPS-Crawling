"""Classification pipeline to process and classify company data."""

from datetime import datetime
import json
import logging
from pathlib import Path

from nps_crawling.classification.preprocess_data import ClassificationDataProcessing
from nps_crawling.classification.model_pipeline import ClassificationModelPipeline
from nps_crawling.config import Config

logger = logging.getLogger(__name__)


class ClassificationPipeline():
    """Classification pipeline class."""

    def __init__(self):
        """Initialize the ClassificationPipeline."""
        # Create version-specific directories on demand
        name = Config.CLASSIFICATION_VERSION
        self.file_dir = Config.CLASSIFIED_BASE_PATH / name / "files"
        (self.file_dir).mkdir(parents=True, exist_ok=True)


        self.get_data = ClassificationDataProcessing()
        self.model_pipeline = ClassificationModelPipeline(
            name=Config.CLASSIFICATION_VERSION,
            classification_configuration=Config.get_classification_configuration_mapping(),
        )

    def classification_workflow(self):
        """Classification workflow method."""

        logger.info("Starting classification")
        self.classified_files = [path.name for path in self.file_dir.iterdir() if path.is_file()]
        json_files = [
            file for file in self.get_data.get_all_json_files()
            if file.name not in self.classified_files
        ]

        total_files = len(json_files)
        logger.info(f"Number of files to classify: {total_files}")

        total_windows_classified = 0

        current_time = datetime.now()
        try:
            for i, json_file in enumerate(json_files, start=1):
                logger.info(f"[{i}/{total_files}] Processing {json_file.name}")
                records = self.get_data.load_file(json_file)

                total_windows_classified += sum(len(record.get("context", [])) for record in records)

                self.model_pipeline.model_workflow(
                    records,
                    source_filename=json_file.stem,
                )
                logger.info(f"[{i}/{total_files}] Finished {json_file.name}")
        except KeyboardInterrupt:
            logger.info("Classification stopped, saving report")

        elapsed_seconds = int((datetime.now() - current_time).total_seconds())
        hours, remainder = divmod(elapsed_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        time_taken = f"{hours}:{minutes:02d}:{seconds:02d} h"
        # Generate summary report
        summary = {
            "experiment_setup": {
                "classification_version": Config.CLASSIFICATION_VERSION,
                "preprocessing_version": Config.PREPROCESSING_VERSION,
            },
            "statistics": {
                "total_files_classified": total_files,
                "total_windows_classified": total_windows_classified,
                "time_taken": time_taken,
            },
        }

        summary_path = Config.CLASSIFIED_BASE_PATH / f"classification_{Config.CLASSIFICATION_VERSION}.json"
        with open(summary_path, "a", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)

        logger.info(f"Classification report saved to {summary_path}")
        logger.info(f"Classification finished in {time_taken}")
        return None
