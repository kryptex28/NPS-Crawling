from __future__ import annotations

from typing import Any, List

from ollama import ChatResponse, Client

from nps_crawling.classification.categories.category import (
    ClassificationCategory,
    DataEntry,
    load_default_classification_category,
)
from nps_crawling.classification.models.model import ClassificationModel, build_llm_system_prompt


class Ollama_LLM(ClassificationModel):
    """Ollama chat API for JSON classification."""

    def __init__(self, model_name: str, model_input: Any = "", **kwargs):
        if not model_input:
            model_input = build_llm_system_prompt(load_default_classification_category())
        super().__init__(model_name, model_input, **kwargs)

        host = self.kwargs.get("host", "localhost")
        port = self.kwargs.get("port", 14000)
        self.client = Client(host=f"{host}:{port}")

    def classify(self, text: str, category: ClassificationCategory) -> List[DataEntry]:
        messages = [
            {"role": "system", "content": build_llm_system_prompt(category)},
            {"role": "user", "content": text},
        ]

        response: ChatResponse = self.client.chat(
            model=self.model_name,
            messages=messages,
            options=self.kwargs.get("options") or {},
        )

        content = response["message"]["content"].strip()
        return category.extract_from_string(content)
