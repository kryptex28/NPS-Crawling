from transformers import AutoModelForCausalLM, AutoTokenizer

from nps_crawling.classification.models.model import ClassificationModel
from nps_crawling.classification.categories.category import (
    ClassificationCategory,
    DataEntry,
)
from nps_crawling.classification.categories.registry import ClassificationTask

class HF_LLM(ClassificationModel):
    """Hugging Face Model class."""
    def __init__(self, model_name: str, **kwargs):
        self.model_input = self._generate_model_input()
        super().__init__(model_name, self.model_input, **kwargs)
        # load the tokenizer and the model
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForCausalLM.from_pretrained(
            model_name,
            torch_dtype="auto",
            device_map="auto",
            cache_dir=self.cache_dir
        )
    
    def _generate_model_input(self) -> dict:
        """Get the model input for the specified category."""
        return {
            ClassificationTask.NPS_CATEGORY:
            """
                You are an expert text classification model for Net Promoter Score (NPS) related statements.

                Task:
                Classify the input text into one or more labels from the list below.
                This is a multi-label classification task, so more than one label can be correct.
                Return a JSON array of label names only.

                Labels:
                - KPI_CURRENT_VALUE: Reports a specific NPS value.
                - KPI_TREND: Describes change over time such as increase, decrease, decline, improvement, or growth.
                - KPI_HISTORICAL_COMPARISON: Explicit numerical comparison to past values such as a year, quarter, or previous period.
                - TARGET_OUTLOOK: Future goals, targets, ambitions, or expected future NPS values.
                - NPS_GOAL_REACHED: States that an NPS target, goal, threshold, or objective has been met or exceeded.
                - METHODOLOGY_DEFINITION: Explains what NPS is, how it is calculated, or what it measures.
                - QUALITATIVE_ONLY: Mentions NPS without numbers, benchmarks, targets, trends, or other clear context.

                Rules:
                1. Return at least one label.
                2. Return every label that is explicitly supported by the text.
                3. Do not infer labels that are not clearly stated.
                4. If the text gives a specific NPS number, include KPI_CURRENT_VALUE.
                5. If the text describes a change over time, include KPI_TREND.
                6. If the text compares against a past period, include KPI_HISTORICAL_COMPARISON.
                7. If the text states a future target or ambition, include TARGET_OUTLOOK.
                8. If the text says a target was reached or exceeded, include NPS_GOAL_REACHED.
                9. If the text explains NPS conceptually, include METHODOLOGY_DEFINITION.
                10. Use QUALITATIVE_ONLY only when NPS is mentioned meaningfully but no stronger label applies.
                11. Return JSON only, with no explanation.

                Output format:
                ["KPI_CURRENT_VALUE", "KPI_TREND"]
            """,
            ClassificationTask.NPS_VALUE_CATEGORY: 
            """
                You are an information extraction classifier specialized in Net Promoter Score (NPS) statements.

                Your task:
                - Extract ALL matching categories from the input text.
                - Multiple categories MAY occur in the same text.
                - Return ONLY valid JSON.
                - Do not explain your reasoning.
                - If no category matches, return {}.
                - Numeric values must be floats.
                - Extract only explicitly stated values.
                - Do not infer or calculate values.

                Categories:

                1. nps_value_fix
                - Extract a direct, unambiguous NPS value.

                2. nps_competition_industry
                - Extract industry benchmark or competitor comparison values.
                - Trigger words may include:
                    "industry average", "benchmark", "competitor", "sector average"

                3. nps_value_over
                - Extract values connected to minimum-threshold wording.
                - Only trigger if signal words appear:
                    "above", "over", "greater than", "more than", "at least"

                4. nps_value_below
                - Extract values connected to maximum-threshold wording.
                - Trigger words:
                    "below", "under", "less than", "at most"

                5. nps_goal_value
                - Extract explicit NPS target values.
                - Trigger words may include:
                    "target", "goal", "aim", "plan to reach", "objective"
                - Only extract values >= 20.

                6. nps_goal_change
                - Extract intended NPS improvement/delta values.
                - Trigger phrases:
                    "improve by", "increase by", "raise by", "grow by"

                Important rules:
                - Multiple categories can appear simultaneously.
                - Return all detected categories in one JSON object.
                - Never return text outside JSON.
                - Use exact property names.
                - Ignore unrelated numbers.
                - Ignore ambiguous NPS references.
                - Ignore percentages unless clearly an NPS value.
                - Prefer the most local value associated with the trigger phrase.

                Examples:

                Input:
                "Our NPS is 60.0."

                Output:
                {
                "nps_value_fix": 60.0
                }

                Input:
                "Our NPS is higher than the industry average of 35.4."

                Output:
                {
                "nps_competition_industry": 35.4
                }

                Input:
                "Our NPS is above 30.0."

                Output:
                {
                "nps_value_over": 30.0
                }

                Input:
                "Our NPS is below 79.7."

                Output:
                {
                "nps_value_below": 79.7
                }

                Input:
                "We aim to improve our NPS to 80.0 next year."

                Output:
                {
                "nps_goal_value": 80.0
                }

                Input:
                "We aim to improve our NPS by 12.5 next year."

                Output:
                {
                "nps_goal_change": 12.5
                }

                Input:
                "Our NPS is 60.0 and above the industry average of 35.4."

                Output:
                {
                "nps_value_fix": 60.0,
                "nps_competition_industry": 35.4
                }

                Input:
                "We aim to improve our NPS by 12.5 and reach 80 next year."

                Output:
                {
                "nps_goal_change": 12.5,
                "nps_goal_value": 80.0
                }

                Input:
                "Our NPS remains below 40 but above 30."

                Output:
                {
                "nps_value_below": 40.0,
                "nps_value_over": 30.0
                }

                Input:
                "The sector benchmark is 45 while our NPS is 61."

                Output:
                {
                "nps_competition_industry": 45.0,
                "nps_value_fix": 61.0
                }

                Now classify the following text:
            """,
            ClassificationTask.HAS_NUMERIC_NPS:
            """
                You are an expert text classifier for Net Promoter Score (NPS) related statements.

                Task:
                Determine whether the input text contains a specific numeric NPS value.
                Return a JSON boolean only: true or false.

                Definitions:
                - has_numeric_nps = true: the text explicitly contains a numeric NPS value (e.g., "NPS is 60", "NPS of 35.4", "NPS: 72").
                - has_numeric_nps = false: the text mentions NPS but does not give a concrete number, or does not mention NPS at all.

                Examples:
                Text: "Our NPS is 60."
                Output: true

                Text: "We aim to improve our NPS next year."
                Output: false

                Text: "Our NPS declined to 45.2 in Q4."
                Output: true

                Text: "NPS is a very important metric."
                Output: false

                Rules:
                1. Return valid JSON only.
                2. Output must be exactly true or false, lowercase, no quotes, no explanation.
                3. Do not infer numbers that are not explicitly stated.
            """             
        }


    def classify(self, text: str, category: ClassificationCategory) -> DataEntry:
        # prepare the model input
        messages = [
            {"role": "system", "content": self.model_input[category.name]},
            {"role": "user", "content": text}
        ]

        text = self.tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
            **self.kwargs
        )
        model_inputs = self.tokenizer([text], return_tensors="pt").to(self.model.device)

        # conduct text completion
        generated_ids = self.model.generate(
            **model_inputs,
            max_new_tokens=32768
        )
        output_ids = generated_ids[0][len(model_inputs.input_ids[0]):].tolist() 

        enable_thinking = self.kwargs.get("enable_thinking", True)
        index = 0
        if enable_thinking:
            # parsing thinking content
            try:
                # rindex finding 151668 (</think>)
                index = len(output_ids) - output_ids[::-1].index(151668)
            except ValueError:
                pass

        content = self.tokenizer.decode(output_ids[index:], skip_special_tokens=True).strip("\n")
        result = category.extract_from_string(content)
        return result