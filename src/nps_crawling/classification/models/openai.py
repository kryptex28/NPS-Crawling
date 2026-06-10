import json

from transformers import AutoModelForCausalLM, AutoTokenizer

from nps_crawling.classification.models.model import ClassificationModel
from nps_crawling.classification.categories.category import (
    ClassificationCategory,
    DataEntry,
)
from nps_crawling.classification.categories.registry import ClassificationTask, get_category

from openai import OpenAI
import hashlib
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)

class OpenAIModel(ClassificationModel):
    """Hugging Face Model class."""
    def __init__(self, model_name: str, **kwargs):
        if "prompt" in kwargs:
            model_input = kwargs["prompt"]
        self.model_input = self._generate_model_input()
        super().__init__(model_name, self.model_input, **kwargs)
        self.model = model_name
        self.client = OpenAI()
        self.predictions = defaultdict(dict)

    def _text_to_key(self, text: str) -> str:
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    def _generate_model_input(self) -> str:
        """Get the model input for the specified category."""
        return f"""
                You are an expert information extraction and classification model specialized in Net Promoter Score (NPS) statements.

                Your task is to analyze the input text and return a single JSON object with the following structure:

                {{
                "{ClassificationTask.NPS_CATEGORY.value}": [],
                "{ClassificationTask.NPS_VALUE_CATEGORY.value}": {{}},
                "{ClassificationTask.HAS_NUMERIC_NPS.value}": false
                }}

                Definitions
                ===========

                1. {ClassificationTask.NPS_CATEGORY.value}

                This is a multi-label classification field.

                Possible labels:

                - KPI_CURRENT_VALUE
                - KPI_TREND
                - KPI_HISTORICAL_COMPARISON
                - TARGET_OUTLOOK
                - NPS_GOAL_REACHED
                - METHODOLOGY_DEFINITION
                - QUALITATIVE_ONLY

                Label rules:

                - KPI_CURRENT_VALUE
                - The text reports a specific NPS value.

                - KPI_TREND
                - The text describes change over time.
                - Examples:
                    - increased
                    - improved
                    - declined
                    - decreased
                    - grew

                - KPI_HISTORICAL_COMPARISON
                - The text explicitly compares NPS against a previous period.
                - Examples:
                    - last year
                    - previous quarter
                    - compared with 2023
                    - up from 45 to 60

                - TARGET_OUTLOOK
                - The text expresses a future goal, target, ambition, forecast, or expected future NPS.

                - NPS_GOAL_REACHED
                - The text states that an NPS target or objective has been met or exceeded.

                - METHODOLOGY_DEFINITION
                - The text explains what NPS is, how it is calculated, or what it measures.

                - QUALITATIVE_ONLY
                - NPS is mentioned meaningfully but none of the above labels apply.

                Rules:

                - Multiple labels may be returned.
                - Return every label explicitly supported by the text.
                - Do not infer unstated labels.
                - If no other label applies but NPS is discussed, return QUALITATIVE_ONLY.
                - At least one label must be returned whenever NPS is mentioned.

                2. {ClassificationTask.NPS_VALUE_CATEGORY.value}

                Extract all explicitly stated NPS-related values.

                Return only categories that are present.

                Supported fields:

                - nps_value_fix
                - Direct NPS value.

                - nps_competition_industry
                - Industry benchmark or competitor value.

                - nps_value_over
                - Threshold values associated with:
                    - above
                    - over
                    - greater than
                    - more than
                    - at least

                - nps_value_below
                - Threshold values associated with:
                    - below
                    - under
                    - less than
                    - at most

                - nps_goal_value
                - Explicit NPS target value.
                - Only extract if value >= 20.

                - nps_goal_change
                - Planned improvement amount.
                - Examples:
                    - improve by 10
                    - increase by 5
                    - raise by 7

                Extraction rules:

                - Numeric values must be floats.
                - Extract only explicitly stated values.
                - Never calculate values.
                - Never infer values.
                - Ignore unrelated numbers.
                - Ignore ambiguous references.
                - Ignore percentages unless clearly an NPS value.
                - Multiple value fields may appear simultaneously.

                3. {ClassificationTask.HAS_NUMERIC_NPS.value}

                Boolean.

                Return true if the text contains at least one explicit numeric NPS value.

                Examples:

                true:
                - "Our NPS is 60."
                - "NPS reached 45.5."
                - "NPS remains above 30."

                false:
                - "We want to improve NPS."
                - "NPS is an important metric."

                Output Rules
                ============

                - Return valid JSON only.
                - Do not include explanations.
                - Do not include markdown.
                - Do not include any text outside JSON.
                - Always return all top-level fields.

                Output Schema
                =============

                {{
                "{ClassificationTask.NPS_CATEGORY.value}": ["LABEL_1", "LABEL_2"],
                "{ClassificationTask.NPS_VALUE_CATEGORY.value}": {{
                    "field_name": 12.3
                }},
                "{ClassificationTask.HAS_NUMERIC_NPS.value}": true
                }}

                Example 1

                Input:
                "Our NPS is 60 and above the industry average of 35."

                Output:
                {{
                "{ClassificationTask.NPS_CATEGORY.value}": ["KPI_CURRENT_VALUE"],
                "{ClassificationTask.NPS_VALUE_CATEGORY.value}": {{
                    "nps_value_fix": 60.0,
                    "nps_competition_industry": 35.0
                }},
                "{ClassificationTask.HAS_NUMERIC_NPS.value}": true
                }}

                Example 2

                Input:
                "We aim to improve our NPS by 10 points and reach 80 next year."

                Output:
                {{
                "{ClassificationTask.NPS_CATEGORY.value}": ["TARGET_OUTLOOK"],
                "{ClassificationTask.NPS_VALUE_CATEGORY.value}": {{
                    "nps_goal_change": 10.0,
                    "nps_goal_value": 80.0
                }},
                "{ClassificationTask.HAS_NUMERIC_NPS.value}": true
                }}

                Example 3

                Input:
                "NPS is a customer loyalty metric."

                Output:
                {{
                "{ClassificationTask.NPS_CATEGORY.value}": ["METHODOLOGY_DEFINITION"],
                "{ClassificationTask.NPS_VALUE_CATEGORY.value}": {{}},
                "{ClassificationTask.HAS_NUMERIC_NPS.value}": false
                }}

                Now analyze the provided text.
            """


    def classify(self, text: str, category: ClassificationCategory) -> DataEntry:
        # prepare the model input
        text_key = self._text_to_key(text)
        try:
            result = self.predictions[text_key][category.name]
            return result
        except KeyError:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.model_input},
                    {"role": "user", "content": text}
                ],
            )
            text_response = response.choices[0].message.content
            result_dict = json.loads(text_response)
            for key in result_dict:
                try:
                    key_category = get_category(key)
                except KeyError:
                    raise ValueError(f"Invalid category in model output: {key}")
                key_response = json.dumps(result_dict[key])
                data_entries = key_category.extract_from_string(key_response)
                self.predictions[text_key][key] = data_entries

        return self.predictions[text_key][category.name]