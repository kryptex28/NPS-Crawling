from enum import Enum
from typing import List

class DataEntry:
    """Data entry class."""
    def __init__(self, column_name: str, value):
        self.column_name = column_name
        self.value = value

    def __repr__(self):
        return f"DataEntry(column_name='{self.column_name}', value={self.value})"

class Example:
    """Example for classification property."""
    def __init__(self, text: str, answer: str):
        self.text = text
        self.answer = answer

class ClassificationProperty:
    """Classification property."""
    def __init__(self, name: str, description: str, examples: List[Example]):
        self.name = name
        self.description = description
        self.examples : List[Example] = []

class ClassificationCategory:
    """Classification category."""
    def __init__(self, name: str, properties: list[ClassificationProperty], default_value: any):
        self.name = name
        self.properties = properties
        self.default_value = default_value

    def is_valid(self, entry: DataEntry) -> bool:
        """Check if entry is valid for this category."""
        pass

    def extract_from_string(self, text: str) -> List[DataEntry]:
        """Extract classification answers from given text."""
        pass

    def normalize_eval(self, labels: List[any], predictions: list[any]) -> tuple:
        """Normalize prediction and label for evaluation."""
        return labels, predictions