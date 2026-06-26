"""Classification model pipeline."""

import json
import hashlib
from pathlib import Path

from nps_crawling.db.db_adapter import DbAdapter
from nps_crawling.classification.models.registry import ClassificationModel
from nps_crawling.classification.categories.category import ClassificationCategory
from nps_crawling.classification.common import (
    config_path_ref,
    load_json_file,
    resolve_config_entry,
    resolve_config_path,
)
from nps_crawling.config import Config
import logging

logger = logging.getLogger(__name__)


class ClassificationModelPipeline(Config):
    """Classification model pipeline class."""

    @staticmethod
    def _iter_configuration_items(classification_configuration):
        if isinstance(classification_configuration, dict):
            return classification_configuration.items()
        return classification_configuration

    @staticmethod
    def _resolve_category(value):
        return resolve_config_entry(
            value,
            from_dict=ClassificationCategory.from_dict,
            from_json=ClassificationCategory.from_json,
        )

    @staticmethod
    def _resolve_model(value):
        return resolve_config_entry(
            value,
            from_dict=ClassificationModel.from_dict,
            from_json=ClassificationModel.from_json,
        )

    def __init__(
            self,
            name : str,
            classification_configuration : 
            dict[str | dict | ClassificationCategory,
                 str | dict | ClassificationModel]
        ):
        """Initializes ClassificationModelPipeline."""
        self.category_model : dict[ClassificationCategory, ClassificationModel] = {}
        self.name = name

        # 1. Parse configuration to extract categories and properties first
        self.classification_properties = {}
        parsed_configs = []
        for key, value in self._iter_configuration_items(classification_configuration):
            category = self._resolve_category(key)

            for prop in category.properties:
                self.classification_properties[prop.name] = prop.type.value

            parsed_configs.append((category, value))

        self.allowed_cols = set(self.classification_properties.keys())

        # 2. Initialize DB Adapter and ensure classifications table exists with these properties
        self.adapter = DbAdapter()
        self.adapter.ensure_table_exists(
            include_classifications=True,
            classification_properties=self.classification_properties
        )

        # 3. Instantiate models and train if necessary
        for category, value in parsed_configs:
            model = self._resolve_model(value)

            self.category_model[category] = model
            if not model.is_trained(category):
                logger.info(f"Training {model.model_name} for {category.name}")
                model.train(category)

        self.out_path = Config.CLASSIFIED_BASE_PATH / self.name

    def to_dict(self):
        return {
            "name": self.name,
            "classification_configuration": [
                {
                    "category": config_path_ref(category.config_path),
                    "model": config_path_ref(model.config_path),
                }
                for category, model in self.category_model.items()
            ],
        }
    
    @classmethod
    def from_dict(cls, data):
        classification_configuration = {}
        for entry in data.get("classification_configuration", []):
            category = cls._resolve_category(entry["category"])
            model = cls._resolve_model(entry["model"])
            classification_configuration[category] = model

        return cls(
            name=data["name"],
            classification_configuration=classification_configuration,
        )

    @classmethod
    def from_json(cls, path: str | Path) -> "ClassificationModelPipeline":
        """Load a pipeline from a JSON file."""
        return cls.from_dict(load_json_file(resolve_config_path(path)))


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
            path_to_classified = str(self.out_path / "files"),    # Pfad für die Haupttabelle (neu!)
            allowed_cols=self.allowed_cols,
            # --- Results ---
            **results
        )

    def model_workflow(self, records, source_filename):
        """Classify all context windows in the given records and save as JSON."""
        total_windows = sum(len(record.get("context", [])) for record in records)
        done = 0

        logger.info(f"Starting file: {source_filename} ({total_windows} windows)")

        default_results = {}
        for category in self.category_model:
            for prop in category.properties:
                default_results[prop.name] = prop.default_value

        for record in records:
            record_results = default_results.copy()
            for window in record.get("context", []):
                for category, model in self.category_model.items():
                    results = model.classify(window["context"], category)
                    for result in results:
                        window[result.column_name] = result.value
                        if result.value != category.get_property(result.column_name).default_value:
                            record_results[result.column_name] = result.value

                done += 1
                logger.info(f"{source_filename}: {done}/{total_windows}")
            self._write_to_db(record["metadata"]["filing"]["id"], record_results)

        file_path = self.out_path / "files" / f"{source_filename}.json"
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(records, f, ensure_ascii=False, indent=2)

        logger.info(f"Finished file: {source_filename}")
