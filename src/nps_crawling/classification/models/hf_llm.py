from typing import List

from transformers import AutoModelForCausalLM, AutoTokenizer

from nps_crawling.classification.models.model import ClassificationModel
from nps_crawling.classification.categories.category import (
    ClassificationCategory,
    DataEntry,
    DEFAULT_FILE
)
from nps_crawling.classification.categories.registry import ClassificationTask
import json

class HF_LLM(ClassificationModel):
    """Hugging Face Model class."""
    def __init__(self, model_name: str, **kwargs):
        with open(DEFAULT_FILE, "r", encoding="utf-8") as f:
            default_category = ClassificationCategory.from_dict(json.load(f))
        self.model_input = self._generate_model_input(default_category)
        super().__init__(model_name, self.model_input, **kwargs)
        # load the tokenizer and the model
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForCausalLM.from_pretrained(
            model_name,
            torch_dtype="auto",
            device_map="auto",
            cache_dir=self.cache_dir
        )
    
    def _generate_model_input(self, classification_category: ClassificationCategory) -> dict:
        """Get the model input for the specified category."""
        prompt_base = classification_category.prompt_base
        labels_str = ""
        for property in classification_category.properties:
            labels_str += f" - {property.name}: {property.description}\n"

        examples_str = ""
        for example in classification_category.examples:
            examples_str += f"Text: {example.text}\n"
            output = {}
            for entry in example.answer:
                output[entry.column_name] = entry.value
            examples_str += f"Output: {json.dumps(output, indent=4)}\n\n"

        output_format = {}
        for property in classification_category.properties:
            output_format[property.name] = property.type.value

        output_format_str = json.dumps(output_format, indent=4)

        prompt = f"{prompt_base}\n\n"
        prompt += f"Labels:\n{labels_str}\n"
        prompt += f"Output Format:\n{output_format_str}\n"
        prompt += "Return valid JSON only, following the output format exactly.\n"
        prompt += "Now classify this text:\n"
        return prompt


    def classify(self, text: str, category: ClassificationCategory) -> List[DataEntry]:
        # prepare the model input
        if category.name not in self.classification_category_names:
            raise ValueError(f"Category '{category.name}' is not supported by this model.")
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