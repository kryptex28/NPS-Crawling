from dataclasses import dataclass

@dataclass
class PromptData:
    prompt_class: str = ""
    prompt: str = ""