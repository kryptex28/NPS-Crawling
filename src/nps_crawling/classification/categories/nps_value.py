import math
import re
from typing import List, Optional

from nps_crawling.classification.categories.category import (
    ClassificationCategory,
    ClassificationProperty,
    Example,
    DataEntry,
)

class NPSValue(ClassificationCategory):
    """NPS Value Category."""
    def __init__(self, name: str):
        properties = [
            ClassificationProperty(
                name="nps_value",
                description="Numeric NPS value extracted from text",
                examples=[
                    Example(
                        text="Our NPS is -10.0.",
                        answer="-10.0"
                    ),
                    Example(
                        text="We aim to improve our NPS to 80.0 next year.",
                        answer="80.0"
                    ),
                    Example(
                        text="Our NPS is higher than the industry average of 35.4.",
                        answer="35.4"
                    ),
                    Example(
                        text="Our NPS is above 30.0.",
                        answer="30.0"
                    ),
                    Example(
                        text="Our NPS is below 79.7.",
                        answer="79.7"
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
            
    def extract_from_string(self, text: str) -> List[DataEntry]:
        """Extract NPS Value from given text."""
        regex = r'^-?(?:100(?:[.,]0+)?|(?:\d{1,2})(?:[.,]\d+)?|0(?:[.,]\d+)?)$'
        entries : List[DataEntry] = []
        for prop in self.properties:
            matches = re.findall(regex, text)
            if matches:
                for match in matches:
                    try:
                        value = float(match.replace(',', '.'))
                        entries.append(DataEntry(column_name=prop.name, value=value))
                    except ValueError:
                        continue
            else:
                entries.append(DataEntry(column_name=prop.name, value=self.default_value))

        return entries
    
    def normalize_eval(self, labels: list[float | None], predictions: list[float | None]) -> tuple[list[str], list[str]]:
        """Normalize prediction and label for evaluation."""
        y_true = [self._to_label(gt, gt) for gt in labels]          # oracle labels
        y_pred = [self._to_label(gt, pred) for gt, pred in zip(labels, predictions)]
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