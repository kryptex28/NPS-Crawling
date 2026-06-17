

from datetime import datetime
from enum import Enum
from pathlib import Path

import pandas as pd
from sklearn.metrics import classification_report
from sklearn.model_selection import train_test_split

from nps_crawling.classification.categories.category import DataEntry, ClassificationCategory
import json
import os
import logging
from nps_crawling.classification.common import make_hashable, stable_serialize
from nps_crawling.config import Config

logger = logging.getLogger(__name__)

import hashlib

SEED = 42

class ClassificationModel:
    """Base class for classification models."""
    _instances = {}
    _registry = {}

    def __new__(cls, model_name: str, model_input: any = "", **kwargs):
        key = (
            cls,
            model_name,
            make_hashable(model_input),
            make_hashable(kwargs)
        )
        if key not in cls._instances:
            instance = super().__new__(cls)
            cls._instances[key] = instance
        return cls._instances[key]

    def __init__(self, model_name: str, model_input: any = "", **kwargs):
        if hasattr(self, '_initialized') and self._initialized:
            return
        self.model_name = model_name
        self.model_input = model_input
        self.kwargs = kwargs
        self._initialized = True
        model_file_name = model_name.split("/")[-1]
        self.config_path = Config.CLASSIFICATION_CONFIG_DIR / model_file_name / f"{self.stable_id}.json"
        if not os.path.exists(self.config_path):
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            with open(self.config_path, "w") as f:
                json.dump(self.to_dict(), f, indent=4)

        self.cache_dir = Config.CLASSIFICATION_CACHE_DIR
    
    def __repr__(self):
        return (
            f"{self.__class__.__name__}("
            f"model_name={self.model_name!r}, "
            f"model_input={self.model_input!r}, "
            f"kwargs={self.kwargs!r})"
        )
    
    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False

        return (
            self.model_name == other.model_name
            and self.model_input == other.model_input
            and self.kwargs == other.kwargs
        )
    
    def __hash__(self):
        return hash((
            self.__class__,
            self.model_name,
            make_hashable(self.model_input),
            make_hashable(self.kwargs)
        ))
    
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        cls._registry[cls.__name__] = cls

    def to_dict(self):
        return {
            "class_name": self.__class__.__name__,
            "model_name": self.model_name,
            "model_input": self.model_input,
            "kwargs": self.kwargs,
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
        subclass = cls._registry[data["class_name"]]

        return subclass(
            model_name=data["model_name"],
            **data.get("kwargs", {})
        )
    
    def classify(self, text: str, category: ClassificationCategory) -> list[DataEntry]:
        """Classify given text according to the specified category."""
        raise NotImplementedError("Subclasses must implement this method.")
    
    def evaluate(self, category: ClassificationCategory, text_column : str, test_size = 0.2) -> list[dict]:
        """Evaluate model performance on given texts and labels."""
        if not category.csv_path:
            raise ValueError("No csv as groundtruth provided")

        df = pd.read_csv(category.csv_path)
        train_df, test_df = train_test_split(df, test_size=test_size, random_state=SEED)
        texts = test_df[text_column].tolist()
        all_data_entries = []
        all_evaluation_results = {}
        time_per_snippet = 0

        current_time = datetime.now()
        for i, text in enumerate(texts):
            logger.info(f"Classifying text {i+1}/{len(texts)}")
            data_entries = self.classify(text, category)
            all_data_entries.append(data_entries)

        time_per_snippet = (datetime.now() - current_time).total_seconds() / len(texts)

        for classification_property in category.properties:
            true_labels = []
            predictions = []
            for i, data_entries in enumerate(all_data_entries):
                for entry in data_entries:
                    if entry.column_name == classification_property.name:
                        logger.debug(f"True label: {df.iloc[i][classification_property.name]}\nPrediction: {entry.value}\n")
                        true_labels.append(df.iloc[i][classification_property.name])
                        predictions.append(entry.value)
                        break


            true_labels, predictions = category.normalize_eval(true_labels, predictions)

            for t, p in zip(true_labels, predictions):
                logger.debug(f"True: {t}, Pred: {p}")

            evaluation_results = classification_report(true_labels, predictions, output_dict=True)
            all_evaluation_results[classification_property.name] = evaluation_results

        config = json.load(open(self.config_path))
        if "evaluation_results" not in config or not isinstance(config["evaluation_results"], dict):
            config["evaluation_results"] = {}
        config["evaluation_results"][category.name] = all_evaluation_results
        config["evaluation_results"][category.name]["time_per_snippet"] = time_per_snippet
        with open(self.config_path, "w") as f:
            json.dump(config, f, indent=4)
        return all_evaluation_results
    
    def train(self, category: ClassificationCategory, text_column : str, test_size = 0.2) -> None:
        """Train SVM model for given classification option."""
        
    