"""Classification model pipeline."""

import json
import hashlib

from nps_crawling.db.db_adapter import DbAdapter
from nps_crawling.classification.models.registry import get_model_from_config, ClassificationModel
from nps_crawling.classification.categories.registry import get_category, ClassificationTask
from nps_crawling.config import Config
import logging

logger = logging.getLogger(__name__)


class ClassificationModelPipeline(Config):
    """Classification model pipeline class."""

    def __init__(self):
        """Initializes ClassificationModelPipeline."""
        super().__init__()

        self.classification_models : dict[ClassificationTask, ClassificationModel] = {}

        for classification_option in self.CLASSIFICATION_CONFIG:
            logger.info(f"Loading Model for: {classification_option}")
            self.classification_models[classification_option] = get_model_from_config(
                self.CLASSIFICATION_CONFIG[classification_option]["config_file"]
            )

        self.adapter = DbAdapter()

        self.out_path = self.NPS_CLASSIFIED_JSON / self.CLASSIFICATION_VERSION

        with open(self.out_path / "config.json", "w", encoding="utf-8") as f:
            json.dump(self.CLASSIFICATION_CONFIG, f, ensure_ascii=False, indent=2)

    def _write_to_db(self, id, results):
        payload = json.dumps(self.CLASSIFICATION_CONFIG, sort_keys=True, separators=(",", ":"))
        experiment_version = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        for key, value in results.items():
            if value == 0:
                results[key] = False
            elif value == 1:
                results[key] = True

        self.adapter.upsert_classification(
            # --- Pflicht- und Metadaten-Felder ---
            filing_id=id,                 # ID des Filings
            version=experiment_version,                          # Deine aktuelle Experiment-Version
            path_to_classified = str(self.NPS_CLASSIFIED_JSON / "files"),    # Pfad für die Haupttabelle (neu!)
            # --- Results ---
            **results
        )

    def model_workflow(self, records, source_filename):
        """Classify all context windows in the given records and save as JSON."""
        total_windows = sum(len(record.get("context", [])) for record in records)
        done = 0

        logger.info(f"Starting file: {source_filename} ({total_windows} windows)")

        default_results = {}
        for classification_option in self.CLASSIFICATION_CONFIG:
            for prop in get_category(classification_option).properties:
                default_results[prop.name] = classification_option.default_value

        for record in records:
            record_results = default_results.copy()
            for window in record.get("context", []):
                for classification_option in self.CLASSIFICATION_CONFIG:
                    model = self.classification_models[classification_option]
                    option = get_category(classification_option)
                    results = model.classify(option, window["context"])
                    for result in results:
                        window[result.column_name] = result.entry
                        if result.entry != option.default_value:
                            record_results[result.column_name] = result.entry
                    
                done += 1
                logger.info(f"{source_filename}: {done}/{total_windows}")
            self._write_to_db(record["filing_id"], record_results)

        file_path = self.out_path / f"{source_filename}.json"
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(records, f, ensure_ascii=False, indent=2)

        logger.info(f"Finished file: {source_filename}")
