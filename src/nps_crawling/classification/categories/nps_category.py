from typing import List

from nps_crawling.classification.categories.category import (
    ClassificationCategory,
    ClassificationProperty,
    Example,
    DataEntry,
)

class NPSCategory(ClassificationCategory):
    """NPS Value Category."""
    def __init__(self, name: str):
        properties = [
            ClassificationProperty(
                name="KPI_CURRENT_VALUE",
                description="Reports a specific NPS value.",
                examples=[
                    Example(
                        text="Our NPS is 60.0.",
                        answer="KPI_CURRENT_VALUE"
                    ),
                ],
            ),
            ClassificationProperty(
                name="KPI_TREND",
                description="Describes change over time (increase, decrease, improvement).",
                examples=[
                    Example(
                        text="The Net Promoter Score declined in 2023.",
                        answer="KPI_TREND"
                    ),
                ],
            ),
            ClassificationProperty(
                name="KPI_HISTORICAL_COMPARISON",
                description="Explicit numerical comparison to past values (year, quarter, etc.).",
                examples=[
                    Example(
                        text="Compared to Q3, our NPS increased by 10%.",
                        answer="KPI_HISTORICAL_COMPARISON"
                    ),
                ],
            ),
            
            ClassificationProperty(
                name="TARGET_OUTLOOK",
                description="Future goals, targets, or ambitions related to NPS.",
                examples=[
                    Example(
                        text="We aim to improve our NPS to 70 next year.",
                        answer="TARGET_OUTLOOK"
                    ),
                ],
            ),
            ClassificationProperty(
                name="NPS_GOAL_REACHED",
                description="Indicates that the company explicitly states it has met or exceeded a predefined NPS target, goal, or threshold.",
                examples=[
                    Example(
                        text="Our annual NPS target was reached.",
                        answer="NPS_GOAL_REACHED"
                    ),
                ],
            ),
            ClassificationProperty(
                name="METHODOLOGY_DEFINITION",
                description="Explains what NPS is or how it works.",
                examples=[
                    Example(
                        text="NPS measures customer loyalty.",
                        answer="METHODOLOGY_DEFINITION"
                    ),
                ],
            ),
            ClassificationProperty(
                name="QUALITATIVE_ONLY",
                description="Mentions NPS without numbers, comparisons, or clear context.",
                examples=[
                    Example(
                        text="NPS is a very important metric for our team.",
                        answer="QUALITATIVE_ONLY"
                    ),
                ],
            ),
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
        for prop in self.properties:
            if prop.name in text:
                entries.append(DataEntry(column_name=prop.name, value=1))
            else:
                entries.append(DataEntry(column_name=prop.name, value=0))

        return entries