"""Ollama LLM class."""
from ollama import ChatResponse, Client

from nps_crawling.llm.llm_base import LLMBase


class LLMOllama(LLMBase):
    """Ollama LLM class."""
    def __init__(self,
                 persona,
                 temperature=0.0,
                 top_p=1.0,
                 top_k=1,
                 num_predict=128,
                 seed=42,
                 repeat_penalty=1.0,
                 model='mistral',
                 host='localhost',
                 port=14000,
                 **kwargs,
                 ):
        """Initialize Ollama LLM class."""
        super().__init__(persona=persona,
                         temperature=temperature,
                         top_k=top_k,
                         top_p=top_p,
                         num_predict=num_predict,
                         seed=seed,
                         repeat_penalty=repeat_penalty,
                         **kwargs)
        self.model = model
        self.host = host
        self.port = port

    def classify(self, text):
        """Classify given text."""
        client = Client(host=f"{self.host}:{self.port}")

        response: ChatResponse = client.chat(
            model=self.model,
            messages=[
                {'role': 'system', 'content': self.persona},
                {'role': 'user', 'content': text},
            ],
            options=self.options,
        )
        return response['message']['content'].strip()
