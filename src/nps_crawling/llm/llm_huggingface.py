"""Huggingface LLM implementation."""
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline

from nps_crawling.llm.llm_base import LLMBase


class LLMHuggingFace(LLMBase):
    """Huggingface LLM class."""
    def __init__(self,
                 persona,
                 temperature=0.0,
                 top_p=1.0,
                 top_k=1,
                 num_predict=128,
                 seed=42,
                 repeat_penalty=1.0,
                 model='mistralai/Mistral-7B-Instruct-v0.3',
                 device=None,
                 **kwargs,
                 ):
        """Initialize Huggingface LLM class."""
        super().__init__(persona=persona,
                         temperature=temperature,
                         top_k=top_k,
                         top_p=top_p,
                         num_predict=num_predict,
                         seed=seed,
                         repeat_penalty=repeat_penalty,
                         **kwargs)
        self.model_name = model
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        if torch.cuda.is_available():
            vram = torch.cuda.get_device_properties(0).total_memory / 1024**3
            print(f"VRAM: {vram:.1f} GB — {torch.cuda.get_device_name(0)}")
        else:
            print("No CUDA GPU detected")

        self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        self.model = AutoModelForCausalLM.from_pretrained(
            self.model_name,
            torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
            device_map="auto",
        )
        self.pipe = pipeline(
            "text-generation",
            model=self.model,
            tokenizer=self.tokenizer,
        )

    def classify(self, text):
        """Classify given text."""
        messages = [
            {"role": "system", "content": self.persona},
            {"role": "user", "content": text},
        ]

        prompt = self.tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
        )

        result = self.pipe(
            prompt,
            max_new_tokens=self.options.get("num_predict", 128),
            temperature=max(self.options.get("temperature", 0.0), 1e-6),  # HF doesn't allow 0.0
            top_p=self.options.get("top_p", 1.0),
            top_k=self.options.get("top_k", 1),
            repetition_penalty=self.options.get("repeat_penalty", 1.0),
            do_sample=self.options.get("temperature", 0.0) > 0,
        )

        generated = result[0]["generated_text"]
        response = generated[len(prompt):].strip()
        return response
