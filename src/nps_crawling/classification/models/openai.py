from __future__ import annotations

from typing import Any, List

from openai import OpenAI

from nps_crawling.classification.categories.category import (
    ClassificationCategory,
    DataEntry,
    load_default_classification_category,
)
from nps_crawling.classification.models.model import ClassificationModel, build_llm_system_prompt


class OpenAIModel(ClassificationModel):
    """OpenAI chat completions (JSON in / out), same prompt flow as other LLMs."""

    def __init__(self, model_name: str, model_input: Any = "", **kwargs):
        if not model_input:
            model_input = build_llm_system_prompt(load_default_classification_category())
        super().__init__(model_name, model_input, **kwargs)
        self.client = OpenAI()

    def classify(self, text: str, category: ClassificationCategory) -> List[DataEntry]:
        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=[
                {"role": "system", "content": build_llm_system_prompt(category)},
                {"role": "user", "content": text},
            ],
            **{k: v for k, v in self.kwargs.items() if k in ("temperature", "top_p", "max_tokens", "seed")},
        )
        text_response = (response.choices[0].message.content or "").strip()
        return category.extract_from_string(text_response)
