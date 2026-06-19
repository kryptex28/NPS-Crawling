"""Classification model pipeline."""

import json
import hashlib
from pathlib import Path
from typing import List

from nps_crawling.db.db_adapter import DbAdapter
from nps_crawling.classification.models.registry import get_model_from_config, ClassificationModel
from nps_crawling.classification.categories.category import ClassificationCategory
from nps_crawling.classification.common import make_hashable, stable_serialize
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
        for key, value in self._iter_configuration_items(classification_configuration):
            if isinstance(key, str) or isinstance(key, Path):
                with open(key, "r", encoding="utf-8") as f:
                    data = json.load(f)
                category = ClassificationCategory.from_dict(data)
            elif isinstance(key, dict):
                category = ClassificationCategory.from_dict(key)
            else:
                category = key
            if isinstance(value, str) or isinstance(value, Path):
                with open(value, "r", encoding="utf-8") as f:
                    data = json.load(f)
                model = ClassificationModel.from_dict(data)
            elif isinstance(value, dict):
                model = ClassificationModel.from_dict(value)
            else:
                model = value
            self.category_model[category] = model
            if not model.is_trained(category):
                logger.info(f"Training {model.model_name} for {category.name}")
                model.train(category)

        self.adapter = DbAdapter()

        self.out_path = Config.CLASSIFIED_BASE_PATH / self.name

        with open(Config.CLASSIFICATION_CONFIG_DIR / f"{name}.json", "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)

    def to_dict(self):
        return {
            "name": self.name,
            "classification_configuration": [
                {
                    "category": stable_serialize(category),
                    "model": stable_serialize(model),
                }
                for category, model in self.category_model.items()
            ],
        }
    
    @property
    def stable_id(self):
        data = {
            "class": self.__class__.__name__,
            "model_name": self.model_name,
            "model_input": stable_serialize(self.model_input),
            "kwargs": stable_serialize(self.kwargs),
        }

        payload = json.dumps(data, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode()).hexdigest()
    
    @classmethod
    def from_dict(cls, data):

        classification_configuration = data.get("classification_configuration", {})
        if isinstance(classification_configuration, list):
            for entry in classification_configuration:
                data = entry["category"]
                classification_configuration = {
                    ClassificationCategory.from_dict(entry["category"]): ClassificationModel.from_dict(entry["model"])
                    for entry in classification_configuration
                }

        return cls(
            name=data["name"],
            classification_configuration=classification_configuration,
        )


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
