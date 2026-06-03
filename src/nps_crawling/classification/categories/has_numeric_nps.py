from typing import List

from nps_crawling.classification.categories.category import (
    ClassificationCategory,
    ClassificationProperty,
    Example,
    DataEntry,
)

class HasNumericNPS(ClassificationCategory):
    """NPS Value Category."""
    def __init__(self, name: str):
        properties = [
            ClassificationProperty(
                name="has_numeric_nps",
                description="Indicates whether the text contains a specific numeric NPS value.",
                examples=[
                    Example(
                        text="Our NPS is 60.",
                        answer="True"
                    ),
                    Example(
                        text="We aim to improve our NPS next year.",
                        answer="False"
                    ),
                ]
            )
        ]
        super().__init__(name=name, properties=properties, default_value=0)

    def is_valid(self, entry: DataEntry) -> bool:
        """Check if entry is valid for this category."""
        for prop in self.properties:
            if entry.column_name == prop.name:
                if entry.value == 0 or entry.value == 1:
                    return True
        return False
            
    def extract_from_string(self, text: str) -> List[DataEntry]:
        """Extract NPS Value from given text."""
        entries : List[DataEntry] = []
        if "True" in text or "true" in text:
            entries.append(DataEntry(column_name="has_numeric_nps", value=1))
        else:
            entries.append(DataEntry(column_name="has_numeric_nps", value=0))

        return entries