

from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional

import pandas as pd
from sklearn.metrics import classification_report
from sklearn.model_selection import train_test_split

from nps_crawling.classification.categories.category import (
    ClassificationCategory,
    ClassificationType,
    DataEntry,
    Example,
)
import json
import os
import logging
from nps_crawling.classification.common import (
    load_json_file,
    make_hashable,
    resolve_config_path,
    stable_serialize,
)
from nps_crawling.config import Config

logger = logging.getLogger(__name__)

import hashlib

# Backwards-compatible alias for code still importing SEED from this module.
SEED = Config.CLASSIFICATION_RANDOM_SEED

class NotTrainedError(Exception):
    """Exception raised when a model is not trained."""
    pass

class NotSupportedError(Exception):
    """Exception raised when a model is not supported."""
    pass

def resolved_category_csv_path(csv_path: str) -> Path:
    """Resolve ``csv_path`` for reading; relative paths are anchored at :attr:`Config.ROOT_DIR`."""
    p = Path(csv_path)
    if not p.is_absolute():
        return Config.ROOT_DIR / p
    return p

def ground_truth_train_test_split(
    df: pd.DataFrame,
    test_size: Optional[float] = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Train/test split consistent with :meth:`ClassificationModel.evaluate`.

    Use the returned **train** frame for few-shot examples so they never overlap
    the hold-out set used for evaluation (same ``test_size`` and CSV).

    ``random_state`` and default ``test_size`` come from :class:`nps_crawling.config.Config`.
    """
    if test_size is None:
        test_size = Config.CLASSIFICATION_GROUND_TRUTH_TEST_SIZE
    return train_test_split(
        df,
        test_size=test_size,
        random_state=Config.CLASSIFICATION_RANDOM_SEED,
    )


def _ground_truth_cell_for_property(row: pd.Series, prop) -> object:
    """Map one CSV cell to a value suitable for :class:`DataEntry` / JSON few-shot."""
    if prop.name not in row.index:
        return prop.default_value
    raw = row[prop.name]
    if pd.isna(raw):
        return prop.default_value
    if isinstance(raw, str) and not raw.strip():
        return prop.default_value
    if prop.type == ClassificationType.BOOLEAN:
        try:
            return bool(int(float(str(raw).replace(",", "."))))
        except (TypeError, ValueError):
            return bool(raw)
    if prop.type == ClassificationType.FLOAT:
        try:
            return float(str(raw).replace(",", "."))
        except (TypeError, ValueError):
            return prop.default_value
    return raw


def ground_truth_row_to_example(
    row: pd.Series,
    text_column: str,
    category: ClassificationCategory,
) -> Example:
    """Build one :class:`Example` from a ground-truth row (snippet + property columns)."""
    text = row[text_column]
    if pd.isna(text):
        text = ""
    else:
        text = str(text)
    answer = [
        DataEntry(column_name=p.name, value=_ground_truth_cell_for_property(row, p))
        for p in category.properties
    ]
    return Example(text=text, answer=answer)


def examples_from_training_split(
    category: ClassificationCategory,
    text_column: Optional[str] = None,
    *,
    test_size: Optional[float] = None,
    max_examples: Optional[int] = None,
    shuffle: bool = True,
    sample_seed: Optional[int] = None,
) -> list[Example]:
    """Sample :class:`Example` instances from the **training** fold only.

    Uses :func:`ground_truth_train_test_split` (same seed and test size as
    :meth:`ClassificationModel.evaluate` / :meth:`ClassificationModel.train` when
    defaults are used). Unset parameters are taken from :class:`nps_crawling.config.Config`.

    ``sample_seed`` only affects shuffling within the training fold, not the split boundary.
    """
    if not category.csv_path:
        raise ValueError("No csv as groundtruth provided")
    if text_column is None:
        text_column = Config.CLASSIFICATION_FEW_SHOT_TEXT_COLUMN
    if test_size is None:
        test_size = Config.CLASSIFICATION_GROUND_TRUTH_TEST_SIZE
    if max_examples is None:
        max_examples = Config.CLASSIFICATION_FEW_SHOT_NUM_EXAMPLES
    if sample_seed is None:
        sample_seed = Config.CLASSIFICATION_FEW_SHOT_SAMPLE_SEED
    
    df = pd.read_csv(resolved_category_csv_path(category.csv_path))
    train_df, _ = ground_truth_train_test_split(df, test_size=test_size)
    train_df = train_df.dropna(subset=[text_column])
    train_df = train_df[train_df[text_column].astype(str).str.strip() != ""]
    if shuffle:
        train_df = train_df.sample(frac=1.0, random_state=sample_seed)
    if max_examples is not None:
        train_df = train_df.head(max_examples)
    return [ground_truth_row_to_example(row, text_column, category) for _, row in train_df.iterrows()]


def build_llm_system_prompt(classification_category: ClassificationCategory) -> str:
    """Build a system prompt for JSON in / JSON out LLM classification.

    Uses :attr:`ClassificationCategory.prompt_base`, property descriptions,
    optional :attr:`ClassificationCategory.examples`, and a schema derived
    from property types (:class:`ClassificationType`).
    """
    prompt_base = (classification_category.prompt_base or "").strip()
    labels_str = ""
    for prop in classification_category.properties:
        labels_str += f" - {prop.name}: {prop.description}\n"

    examples_str = ""
    for example in classification_category.examples:
        output = {}
        for entry in example.answer:
            output[entry.column_name] = entry.value
        examples_str += f"Text: {example.text}\nOutput: {json.dumps(output, ensure_ascii=False)}\n\n"

    output_format = {prop.name: prop.type.value for prop in classification_category.properties}

    parts: list[str] = []
    if prompt_base:
        parts.append(prompt_base)
        parts.append("")

    parts.append("Labels (one JSON field per label below):")
    parts.append(labels_str.rstrip())
    parts.append("")

    if examples_str.strip():
        parts.append("Examples:")
        parts.append(examples_str.rstrip())
        parts.append("")

    parts.append(
        "Output format — types show the JSON type for each field; "
        "return one JSON object with exactly these keys:"
    )
    parts.append(json.dumps(output_format, indent=2, ensure_ascii=False))
    parts.append("")
    parts.append(
        "Return valid JSON only: a single object with every key above. "
        "Use true/false for boolean fields. No markdown fences, no commentary."
    )
    return "\n".join(parts)


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
        from nps_crawling.classification.common import classification_config_basename

        if Config.CLASSIFICATION_CONFIG_USE_NAME_FILES:
            stem = f"{self.__class__.__name__}__{classification_config_basename(model_name)}"
            self.config_path = Config.CLASSIFICATION_CONFIG_DIR / f"{stem}.json"
        else:
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
        kwargs = dict(data.get("kwargs", {}))
        model_input = data.get("model_input", "")
        return subclass(data["model_name"], model_input, **kwargs)

    @classmethod
    def from_json(cls, path: str | Path) -> "ClassificationModel":
        """Load a model from a JSON file."""
        return cls.from_dict(load_json_file(resolve_config_path(path)))
    
    def classify(self, text: str, category: ClassificationCategory) -> list[DataEntry]:
        """Classify given text according to the specified category."""
        raise NotImplementedError("Subclasses must implement this method.")
    
    def evaluate(
        self,
        category: ClassificationCategory,
        text_column: str = Config.CLASSIFICATION_FEW_SHOT_TEXT_COLUMN,
        test_size: Optional[float] = Config.CLASSIFICATION_GROUND_TRUTH_TEST_SIZE,
    ) -> list[dict]:
        """Evaluate model performance on given texts and labels."""
        if not category.csv_path:
            raise ValueError("No csv as groundtruth provided")
        if test_size is None:
            test_size = Config.CLASSIFICATION_GROUND_TRUTH_TEST_SIZE

        df = pd.read_csv(resolved_category_csv_path(category.csv_path))
        _, test_df = ground_truth_train_test_split(df, test_size=test_size)
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
                        logger.debug(
                            f"True label: {test_df.iloc[i][classification_property.name]}\n"
                            f"Prediction: {entry.value}\n"
                        )
                        true_labels.append(test_df.iloc[i][classification_property.name])
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
    
    def train(
        self,
        category: ClassificationCategory,
        text_column: str = Config.CLASSIFICATION_FEW_SHOT_TEXT_COLUMN,
        test_size: Optional[float] = Config.CLASSIFICATION_GROUND_TRUTH_TEST_SIZE,
    ) -> None:
        """Train SVM model for given classification option."""
        pass

    def is_trained(self, category: ClassificationCategory) -> bool:
        return True
    
    def is_supported(self, category: ClassificationCategory) -> bool:
        return True
