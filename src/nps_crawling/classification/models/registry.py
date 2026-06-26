from enum import Enum
from nps_crawling.classification.models.model import ClassificationModel
from nps_crawling.classification.models.hf_llm import HF_LLM
from nps_crawling.classification.models.ollama_llm import Ollama_LLM
from nps_crawling.classification.models.bge_base import BGE_Base
from nps_crawling.classification.models.bge_advanced import BGE_Advanced
from nps_crawling.classification.models.deberta_base import DeBERTa_Base
from nps_crawling.classification.models.qwen_advanced import QWEN_Advanced
from nps_crawling.classification.models.openai import OpenAIModel

class ClassificationModelName(str, Enum):
    """Enumeration of classification model names."""
    HF_LLM = "Hugging Face LLM"
    Ollama_LLM = "Ollama LLM"
    BGE_BASE = "BGE Base"
    BGE_ADVANCED = "BGE Advanced"
    DEBERTA_BASE = "DeBERTa Base"
    QWEN_ADVANCED = "QWEN Advanced"
    OPENAI = "OpenAI"
    def __repr__(self):
        return self.value

_MODEL_REGISTRY = {
    ClassificationModelName.HF_LLM: HF_LLM,
    ClassificationModelName.Ollama_LLM: Ollama_LLM,
    ClassificationModelName.BGE_BASE: BGE_Base,
    ClassificationModelName.BGE_ADVANCED: BGE_Advanced,
    ClassificationModelName.DEBERTA_BASE: DeBERTa_Base,
    ClassificationModelName.QWEN_ADVANCED: QWEN_Advanced,
    ClassificationModelName.OPENAI: OpenAIModel,
}

def get_model(model_class_name: ClassificationModelName, model_name: str, **kwargs) -> ClassificationModel:
    """Get model instance by name."""
    if model_class_name not in _MODEL_REGISTRY:
        raise ValueError(f"Model '{model_class_name}' is not registered.")
    model_class = _MODEL_REGISTRY[model_class_name]
    return model_class(model_name, **kwargs)

def get_model_from_config(config_path: str):
    """Get model instance from a JSON config file."""
    return ClassificationModel.from_json(config_path)