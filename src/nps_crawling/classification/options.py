from abc import ABC, abstractmethod
from enum import Enum
from typing import List

class ClassificationProperty():
    """Class for classification properties."""
    def __init__(self, name: str, options: list, description = "", example = ""):
        self.name = name
        self.options = options
        self.description = description
        self.example = example

class ClassificationOption(ABC):

    @abstractmethod
    def get_classification_properties(self) -> List[ClassificationProperty]:
        """Get classification properties."""
        pass

    @abstractmethod
    def get_persona(self) -> List[ClassificationProperty]:
        """Get persona."""
        pass

class NPSCategory(ClassificationOption):

    def get_classification_properties(self) -> List[ClassificationProperty]:
        """Get classification properties for NPS category."""
        return [
            ClassificationProperty(
                name="KPI_CURRENT_VALUE",
                options=[0, 1],
                description="Reports a specific NPS value.",
                example="We achieved a Net Promoter Score of 60.",
            ),
            ClassificationProperty(
                name="KPI_TREND",
                options=[0, 1],
                description="Describes change over time (increase, decrease, improvement).",
                example="The Net Promoter Score declined in 2023.",
            ),
            ClassificationProperty(
                name="KPI_HISTORICAL_COMPARISON",
                options=[0, 1],
                description="Explicit comparison to past values (year, quarter, etc.).",
                example="Compared to Q3, our NPS increased by 10%.",
            ),
            ClassificationProperty(
                name="BENCHMARK_COMPARISON_POSITIVE",
                options=[0, 1],
                description="NPS is described as higher than or outperforming competitors, industry, or benchmarks.",
                example="Our NPS is higher than the industry average.",
            ),
            ClassificationProperty(
                name="BENCHMARK_COMPARISON_NEGATIVE",
                options=[0, 1],
                description="NPS is described as lower than or underperforming relative to competitors, industry, or benchmarks.",
                example="Our NPS is below the industry average.",
            ),
            ClassificationProperty(
                name="TARGET_OUTLOOK",
                options=[0, 1],
                description="Future goals, targets, or ambitions related to NPS.",
                example="We aim to improve our NPS to 70 next year.",
            ),
            ClassificationProperty(
                name="NPS_GOAL_REACHED",
                options=[0, 1],
                description="Indicates that the company explicitly states it has met or exceeded a predefined NPS target, goal, or threshold.",
                example="Our annual NPS target was reached.",
            ),
            ClassificationProperty(
                name="MGMT_COMPENSATION_GOVERNANCE",
                options=[0, 1],
                description="NPS linked to compensation, incentives, or governance.",
                example=r"20% of the incentive plan is based on Net Promoter Score.",
            ),
            ClassificationProperty(
                name="CUSTOMER_CASE_EVIDENCE",
                options=[0, 1],
                description="NPS used in customer stories, testimonials, or case examples.",
                example="Our tool helped a retailer boost its NPS by 10 points.",
            ),
            ClassificationProperty(
                name="NPS_SERVICE_PROVIDER",
                options=[0, 1],
                description="Company provides NPS-related services or tools.",
                example="We provide consulting on Net Promoter Score programs.",
            ),
            ClassificationProperty(
                name="METHODOLOGY_DEFINITION",
                options=[0, 1],
                description="Explains what NPS is or how it works.",
                example="NPS measures customer loyalty.",
            ),
            ClassificationProperty(
                name="QUALITATIVE_ONLY",
                options=[0, 1],
                description="Mentions NPS without numbers, comparisons, or clear context.",
                example="NPS is a very important metric for our team.",
            ),
            ClassificationProperty(
                name="OTHER",
                options=[0, 1],
                description="Does not fit any categories.",
                example="NPS is a Company dedicated to automotive.",
            )
        ]
    
    def get_persona(self) -> str:
        """Get persona for NPS category."""
        persona: str = ("You are a net promoter score text classifier.\n"
            "Task: Given an input context window, assign exactly ONE or more categories describing how the net promoter score (NPS) is referenced:\n"
        )
        for option in self.get_classification_properties():
            persona += f"Label: {option.name}\n Description: {option.description}\n"

        persona += "Output: The chosen category label(s) and nothing else."
            


class HasNumericNPS(ClassificationOption):

    def get_classification_properties(self) -> List[ClassificationProperty]:
        """Get classification properties for has numeric NPS."""
        return [
            ClassificationProperty(
                name="has_numeric_nps",
                options=[0, 1],
                description="Indicates whether the text contains a specific numeric NPS value.",
                example="Our NPS is 60.",
            )
        ]
    
    def get_persona(self):
        """Get persona for has numeric NPS."""
        return ("You are a net promoter score text classifier.\n"
            "Task: Given an input context window, determine if it contains a specific numeric NPS value.\n"
            "Output: 1 if it does, 0 if it does not."
        )

class NPSValue(ClassificationOption):

    def get_classification_properties(self) -> List[ClassificationProperty]:
        """Get classification properties for NPS value."""
        return [
            ClassificationProperty(
                name="nps_value_fix",
                options=r"r'\b(?:100(?:[.,]0+)?|(?:\d{1,2})(?:[.,]\d+)?)\b'",
                description="What is the numeric NPS value?",
                example="Text: Our NPS is 60. Answer: 60.",
            )
        ]
    
    def get_persona(self):
        """Get persona for NPS value."""
        return ("You are a net promoter score text classifier.\n"
            "Task: Given an input context window, extract the specific numeric NPS value mentioned in the text. The NPS value is a floating number between 0 and 100.\n"
            "Output: The numeric NPS value if mentioned, or -1 if no specific numeric NPS value is present."
        )

class ClassificationOptionName(str, Enum):
    """Enum for classification labels."""
    NPS_CATEGORY = "nps_category"
    HAS_NUMERIC_NPS = "has_numeric_nps"
    NPS_VALUE = "nps_value"

_CLASSIFICATION_OPTIONS_MAP = {
    ClassificationOptionName.NPS_CATEGORY: NPSCategory,
    ClassificationOptionName.HAS_NUMERIC_NPS: HasNumericNPS,
    ClassificationOptionName.NPS_VALUE: NPSValue,
}

def get_classification_option(option_name: ClassificationOptionName) -> ClassificationOption:
    """Get classification option by name."""
    option_class = _CLASSIFICATION_OPTIONS_MAP.get(option_name)
    if option_class is None:
        raise ValueError(f"Classification option {option_name} not found.")
    return option_class()
