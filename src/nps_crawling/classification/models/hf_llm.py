from __future__ import annotations

from typing import Any, List

from transformers import AutoModelForCausalLM, AutoTokenizer

from nps_crawling.classification.categories.category import (
    ClassificationCategory,
    DataEntry,
    load_default_classification_category,
)
from nps_crawling.classification.models.model import ClassificationModel, build_llm_system_prompt


class HF_LLM(ClassificationModel):
    """Hugging Face causal LM for JSON classification."""

    def __init__(self, model_name: str, model_input: Any = "", **kwargs):
        if not model_input:
            model_input = build_llm_system_prompt(load_default_classification_category())
        super().__init__(model_name, model_input, **kwargs)

        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForCausalLM.from_pretrained(
            model_name,
            torch_dtype="auto",
            device_map="auto",
            cache_dir=self.cache_dir,
        )

    def classify(self, text: str, category: ClassificationCategory) -> List[DataEntry]:
        system_prompt = build_llm_system_prompt(category)
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": text},
        ]

        chat_template_kwargs = {
            k: v
            for k, v in self.kwargs.items()
            if k in ("enable_thinking", "thinking", "tools", "documents")
        }
        rendered = self.tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
            **chat_template_kwargs,
        )
        model_inputs = self.tokenizer([rendered], return_tensors="pt").to(self.model.device)

        gen_kwargs = {k: v for k, v in self.kwargs.items() if k not in chat_template_kwargs}
        generated_ids = self.model.generate(
            **model_inputs,
            max_new_tokens=gen_kwargs.pop("max_new_tokens", 4096),
            **gen_kwargs,
        )
        output_ids = generated_ids[0][len(model_inputs.input_ids[0]) :].tolist()

        enable_thinking = self.kwargs.get("enable_thinking", True)
        index = 0
        if enable_thinking:
            try:
                index = len(output_ids) - output_ids[::-1].index(151668)
            except ValueError:
                pass

        content = self.tokenizer.decode(output_ids[index:], skip_special_tokens=True).strip("\n")
        return category.extract_from_string(content)
