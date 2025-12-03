from abc import ABC, abstractmethod

class LLMBase(ABC):
    """LLM Base abstract class."""
    @abstractmethod
    def __init__(self,
                 persona,
                 temperature=0.0,
                 top_p=1.0,
                 top_k=1,
                 num_predict=128,
                 seed=42,
                 repeat_penalty=1.0,
                 **kwargs):
        self.persona = persona
        self.options = {
            'temperature': temperature,
            'top_p': top_p,
            'top_k': top_k,
            'num_predict': num_predict,
            'seed': seed,
            'repeat_penalty': repeat_penalty,
        }
        self.options.update(kwargs)

    @abstractmethod
    def classify(self, text):
        pass