from __future__ import annotations

import logging
from typing import Any, List

from transformers import AutoModelForCausalLM, AutoTokenizer

from nps_crawling.classification.categories.category import (
    ClassificationCategory,
    DataEntry,
    load_default_classification_category,
)
from nps_crawling.classification.models.model import ClassificationModel, build_llm_system_prompt
from nps_crawling.config import Config

logger = logging.getLogger(__name__)


class LLM(ClassificationModel):
    """Hugging Face causal LM for JSON classification."""

    def __init__(self, model_name: str, model_input: Any = "", **kwargs):
        if not model_input:
            model_input = build_llm_system_prompt(load_default_classification_category())
        super().__init__(model_name, model_input, **kwargs)

        self.tokenizer = AutoTokenizer.from_pretrained(model_name, padding_side="left")
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token
        self.model = AutoModelForCausalLM.from_pretrained(
            model_name,
            torch_dtype="auto",
            device_map="auto",
            cache_dir=self.cache_dir,
        )
        self.model.eval()
        self._system_prompt_cache: dict[ClassificationCategory, str] = {}

    def _render_prompt(self, text: str, category: ClassificationCategory) -> str:
        if category not in self._system_prompt_cache:
            self._system_prompt_cache[category] = build_llm_system_prompt(category)
        messages = [
            {"role": "system", "content": self._system_prompt_cache[category]},
            {"role": "user", "content": text},
        ]

        chat_template_kwargs = {
            k: v
            for k, v in self.kwargs.items()
            if k in ("enable_thinking", "thinking", "tools", "documents")
        }
        return self.tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
            **chat_template_kwargs,
        )

    def _extract_content(self, output_ids: list[int]) -> str:
        enable_thinking = self.kwargs.get("enable_thinking", True)
        index = 0
        if enable_thinking:
            try:
                index = len(output_ids) - output_ids[::-1].index(151668)
            except ValueError:
                pass
        return self.tokenizer.decode(output_ids[index:], skip_special_tokens=True).strip("\n")

    def classify(self, text: str, category: ClassificationCategory) -> List[DataEntry]:
        return self.classify_batch([text], category)[0]

    def classify_batch(
        self,
        texts: list[str],
        category: ClassificationCategory,
    ) -> list[List[DataEntry]]:
        chat_template_keys = ("enable_thinking", "thinking", "tools", "documents")
        gen_kwargs = {k: v for k, v in self.kwargs.items() if k not in chat_template_keys}
        max_new_tokens = gen_kwargs.pop("max_new_tokens", 4096)

        batch_size = Config.CLASSIFICATION_LLM_BATCH_SIZE
        results: list[List[DataEntry]] = []
        for start in range(0, len(texts), batch_size):
            batch = texts[start : start + batch_size]
            rendered = [self._render_prompt(text, category) for text in batch]
            model_inputs = self.tokenizer(
                rendered,
                return_tensors="pt",
                padding=True,
            ).to(self.model.device)

            generated_ids = self.model.generate(
                **model_inputs,
                max_new_tokens=max_new_tokens,
                pad_token_id=self.tokenizer.pad_token_id,
                **gen_kwargs,
            )

            input_length = model_inputs.input_ids.shape[1]
            for row in generated_ids:
                content = self._extract_content(row[input_length:].tolist())
                results.append(category.extract_from_string(content))

            logger.info(
                f"{self.model_name}: {category.name} classified "
                f"{min(start + batch_size, len(texts))}/{len(texts)}"
            )

        return results
