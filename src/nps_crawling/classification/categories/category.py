from enum import Enum
import hashlib
import json
import math
import os
from pathlib import Path
import re
from typing import List, Optional
from nps_crawling.classification.common import make_hashable, stable_serialize

import logging
logger = logging.getLogger(__name__)

current_dir = Path(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_FILE = current_dir.parent / "configurations" / "categories" / "Default" / "1661ea62d36667f0ef1f0c1ea6fd5281231de88e9e3d016b71bb1e55f8831688.json"

class ClassificationType(str, Enum):
    """Classification types."""
    BOOLEAN = "boolean"
    FLOAT = "float"

    def __repr__(self):
        return self.value

class DataEntry:
    """Data entry class."""
    def __init__(self, column_name: str, value):
        self.column_name = column_name
        self.value = value

    def __repr__(self):
        return (
            f"{self.__class__.__name__}("
            f"column_name={self.column_name!r}, "
            f"value={self.value!r}, "
        )

    def to_dict(self):
        return {
            "column_name": self.column_name,
            "value": self.value,
        }
    
    @classmethod
    def from_dict(cls, data):
        return cls(
            column_name=data["column_name"],
            value=data["value"],
        )
    
class Example:
    """Example for classification property."""
    def __init__(self, text: str, answer: List[DataEntry]):
        self.text = text
        self.answer = answer

    def __repr__(self):
        return (
            f"{self.__class__.__name__}("
            f"text={self.text!r}, "
            f"answer={self.answer!r}, "
        )

    def to_dict(self):
        return {
            "text" : self.text,
            "answer" : stable_serialize(self.answer)
        }
    
    @classmethod
    def from_dict(cls, data):
        return cls(
            text = data["text"],
            answer = [DataEntry.from_dict(entry) for entry in data["answer"]]
        )

class ClassificationProperty:
    """Classification property."""
    def __init__(self, name: str, description: str, type: ClassificationType):
        self.name = name
        self.description = description
        self.type : ClassificationType = type
        if self.type == ClassificationType.BOOLEAN:
            self.default_value = 0
        else:
            self.default_value = None

    def __repr__(self):
        return (
            f"{self.__class__.__name__}("
            f"name={self.name!r}, "
            f"description={self.description!r}, "
            f"type={self.type!r})"
        )
    
    def to_dict(self):
        return {
            "name": self.name,
            "description": self.description,
            "type": self.type,
        }
    
    @classmethod
    def from_dict(cls, data):
        return cls(
            name=data["name"],
            description=data["description"],
            type=ClassificationType(data["type"])
        )
    
    def cast_value(self, value : any):
        exception = None
        value = self.default_value
        if self.type == ClassificationType.BOOLEAN:
            try:
                value = bool(value)
            except Exception as e:
                exception = e
        elif self.type == ClassificationType.FLOAT:
            try:
                value = str(value).replace(",", ".")
                value = float(value)
            except Exception as e:
                exception = e
        else:
            exception = ValueError(f"{self.type} is not implemented.")

        if exception:
            logger.warning(f"Value {value} was not valid:\n{e}\nReturning{self.default_value}")
            return self.default_value
        
        return value
        


class ClassificationCategory:
    """Classification category."""
    _registry = {}
    def __init__(
            self,
            name: str,
            properties: list[ClassificationProperty],
            prompt_base: str,
            csv_path: Optional[str] = None,
            examples: List[Example] = []
        ):
        self.name = name
        self.properties = properties
        self.prompt_base = prompt_base
        self.csv_path = csv_path
        self.examples = examples
        current_dir = Path(os.path.dirname(os.path.abspath(__file__)))
        self.config_path = current_dir.parent / "configurations" / "categories" / name / f"{self.stable_id}.json"
        if not os.path.exists(self.config_path):
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            with open(self.config_path, "w") as f:
                json.dump(self.to_dict(), f, indent=4)
    
    def __repr__(self):
        return (
            f"{self.__class__.__name__}("
            f"name={self.name!r}, "
            f"properties={self.properties!r}, "
            f"prompt_base={self.prompt_base!r}, "
            f"csv_path={self.csv_path!r}, "
            f"examples={self.examples!r})"
        )
    
    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False

        return (
            self.name == other.name
            and self.properties == other.properties
            and self.prompt_base == other.prompt_base
            and self.csv_path == other.csv_path
            and self.examples == other.examples
        )
    
    def __hash__(self):
        return hash((
            self.__class__,
            self.name,
            tuple(make_hashable(prop) for prop in self.properties),
            make_hashable(self.prompt_base),
            make_hashable(self.csv_path),
            make_hashable(self.examples)
        ))

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        cls._registry[cls.__name__] = cls

    def to_dict(self):
        return {
            "class_name": self.__class__.__name__,
            "name": self.name,
            "properties": stable_serialize(self.properties),
            "prompt_base": self.prompt_base,
            "csv_path": self.csv_path,
            "examples" : stable_serialize(self.examples)
        }
    
    @property
    def stable_id(self):
        data = {
            "class": self.__class__.__name__,
            "name": self.name,
            "properties": stable_serialize(self.properties),
            "prompt_base": stable_serialize(self.prompt_base),
            "csv_path": stable_serialize(self.csv_path),
            "examples" : stable_serialize(self.examples)
        }

        payload = json.dumps(data, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode()).hexdigest()
    
    @classmethod
    def from_dict(cls, data):

        return cls(
            name=data["name"],
            properties=[ClassificationProperty.from_dict(prop_data) for prop_data in data["properties"]],
            prompt_base=data["prompt_base"],
            csv_path=data["csv_path"],
            examples=[Example.from_dict(example_data) for example_data in data.get("examples", [])]
        )

    def is_valid(self, entry: DataEntry) -> bool:
        """Check if entry is valid for this category."""
        pass

    def _str_to_dict(self, text: str) -> dict:
        if not text or not text.strip():
            return {}

        # Remove markdown code fences if present
        cleaned = re.sub(r"```(?:json)?", "", text)
        cleaned = cleaned.replace("```", "").strip()

        try:
            data = json.loads(cleaned)

            if not isinstance(data, dict):
                return {}

            result = {}

            for key, value in data.items():
                result[str(key)] = value

            return result

        except Exception as e:
            logger.warning(f"JSON could not be loaded, taking defaults.\n{e}")
            return {}

    def get_property(self, name : str):
        for property in self.properties:
            if property.name == name:
                return property
        raise ValueError(f"Column name does not match any property name {name}")

    def extract_from_string(self, text: str) -> List[DataEntry]:
        """Extract classification answers from given text."""
        entries : List[DataEntry] = []
        extracted_dict = self._str_to_dict(text)
        for prop in self.properties:
            if prop.name in extracted_dict:
                value = extracted_dict[prop.name]
                value = prop.cast_value(value)
                entries.append(DataEntry(column_name=prop.name, value=value))
            else:
                entries.append(DataEntry(column_name=prop.name, value=prop.default_value))

        return entries

    def normalize_eval(self, labels: list[float | None], predictions: list[float | None]) -> tuple[list[str], list[str]]:
        """Normalize prediction and label for evaluation."""
        is_float = any(isinstance(label, float) for label in labels if label is not None)
        if is_float:
            logger.debug("Normalizing evaluation results:")
            for gt, pred in zip(labels, predictions):
                logger.debug(f"GT: {gt}, Pred: {pred}")
            y_true = [self._to_label(gt, gt) for gt in labels]          # oracle labels
            y_pred = [self._to_label(gt, pred) for gt, pred in zip(labels, predictions)]
            logger.debug("Normalized labels and predictions:")
            for t, p in zip(y_true, y_pred):
                logger.debug(f"True: {t}, Pred: {p}")
            return y_true, y_pred

        return labels, predictions
    
    def _is_close(self, a: Optional[float], b: Optional[float], tol=1e-5) -> bool:
        if a is None and b is None:
            return True
        if a is None or b is None:
            return False
        return math.isclose(a, b, abs_tol=tol)

    def _to_label(self,gt: Optional[float], pred: Optional[float]) -> str:
        if pred is None:
            return "no_value"
        elif self._is_close(gt, pred):
            return "correct_value"
        else:
            return "wrong_value"