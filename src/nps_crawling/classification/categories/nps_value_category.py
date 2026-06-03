import math
from typing import List, Optional

from matplotlib import text

from nps_crawling.classification.categories.category import (
    ClassificationCategory,
    ClassificationProperty,
    Example,
    DataEntry,
)

import json
import re
import logging

logger = logging.getLogger(__name__)

class NPSValueCategory(ClassificationCategory):
    """NPS Value Category."""
    def __init__(self, name: str):
        properties = [
            ClassificationProperty(
                name="nps_value_fix",
                description="Unambiguous, valid NPS value",
                examples=[
                    Example(
                        text="Our NPS is 60.0.",
                        answer="{'nps_value_fix' : 60.0}"
                    )
                ]
            ),
            ClassificationProperty(
                name="nps_competition_industry",
                description="Benchmark/industry context detected",
                examples=[
                    Example(
                        text="Our NPS is higher than the industry average of 35.4.",
                        answer="{'nps_competition_industry' : 35.4}"
                    )
                ]
            ),
            ClassificationProperty(
                name="nps_value_over",
                description="Minimum value from NPS series/quarter tables, only if signal words like 'above/over' appear",
                examples=[
                    Example(
                        text="Our NPS is above 30.0.",
                        answer="{'nps_value_over' : 30.0}"
                    )
                ]
            ),
            ClassificationProperty(
                name="nps_value_below",
                description="Value extracted from 'below/under/less than …'",
                examples=[
                    Example(
                        text="Our NPS is below 79.7.",
                        answer="{'nps_value_below' : 79.7}"
                    )
                ],
            ),
            ClassificationProperty(
                name="nps_goal_value",
                description="Explicit NPS target (≥ 20)",
                examples=[
                    Example(
                        text="We aim to improve our NPS to 80.0 next year.",
                        answer="{'nps_goal_value' : 80.0}"
                    )
                ],
            ),
            ClassificationProperty(
                name="nps_goal_change",
                description="Change target (e.g., 'improve by 30')",
                examples=[
                    Example(
                        text="We aim to improve our NPS by 12.5 next year.",
                        answer="{'nps_goal_change' : 12.5}"
                    )
                ]
            )
        ]
        super().__init__(name=name, properties=properties, default_value=None)

    def is_valid(self, entry: DataEntry) -> bool:
        """Check if entry is valid for this category."""
        for prop in self.properties:
            if entry.column_name == prop.name:
                if isinstance(entry.value, float) and entry.value >= -100 and entry.value <= 100:
                    return True
                elif entry.value == self.default_value:
                    return True
        return False
    
    def _to_data_entries(self, obj) -> List[DataEntry]:
        entries = []

        if isinstance(obj, dict):
            if "label" in obj:
                label = obj["label"]
                value = obj.get("value")
                if label is not None:
                    # try to convert label to float (supports negative values)
                    try:
                        converted = float(label)
                    except (TypeError, ValueError):
                        converted = None
                    entries.append(DataEntry(column_name=label, value=converted if converted is not None else value))
            elif "items" in obj and isinstance(obj["items"], list):
                for item in obj["items"]:
                    if isinstance(item, dict) and "label" in item:
                        label = item["label"]
                        value = item.get("value")
                        try:
                            converted = float(label)
                        except (TypeError, ValueError):
                            converted = None
                        entries.append(
                            DataEntry(
                                column_name=label,
                                value=converted if converted is not None else value
                            )
                        )
        return entries
            
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
                try:
                    result[str(key)] = float(value)
                except (TypeError, ValueError):
                    continue

            return result

        except json.JSONDecodeError:
            return {}

    def extract_from_string(self, text: str) -> List[DataEntry]:
        """Extract NPS Value from given text."""
        entries : List[DataEntry] = []
        extracted_dict = self._str_to_dict(text)
        for prop in self.properties:
            if prop.name in extracted_dict:
                value = extracted_dict[prop.name]
                if isinstance(value, float) and value >= -100 and value <= 100:
                    entries.append(DataEntry(column_name=prop.name, value=value))
                else:
                    entries.append(DataEntry(column_name=prop.name, value=self.default_value))
            else:
                entries.append(DataEntry(column_name=prop.name, value=self.default_value))

        return entries
    
    def normalize_eval(self, labels: list[float | None], predictions: list[float | None]) -> tuple[list[str], list[str]]:
        """Normalize prediction and label for evaluation."""
        logger.debug("Normalizing evaluation results:")
        for gt, pred in zip(labels, predictions):
            logger.debug(f"GT: {gt}, Pred: {pred}")
        y_true = [self._to_label(gt, gt) for gt in labels]          # oracle labels
        y_pred = [self._to_label(gt, pred) for gt, pred in zip(labels, predictions)]
        logger.debug("Normalized labels and predictions:")
        for t, p in zip(y_true, y_pred):
            logger.debug(f"True: {t}, Pred: {p}")
        return y_pred, y_true
    
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