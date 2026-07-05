from enum import Enum
from nps_crawling.classification.models.model import ClassificationModel
from nps_crawling.classification.models.llm import LLM
from nps_crawling.classification.models.ollama_llm import Ollama_LLM
from nps_crawling.classification.models.bge_base import BGE_Base
from nps_crawling.classification.models.bge_advanced import BGE_Advanced
from nps_crawling.classification.models.deberta_base import DeBERTa_Base
from nps_crawling.classification.models.qwen_advanced import QWEN_Advanced
from nps_crawling.classification.models.qwen_candidate import QWEN_Candidate
from nps_crawling.classification.models.svm import SVM
from nps_crawling.classification.models.openai import OpenAIModel

class ClassificationModelName(str, Enum):
    """Enumeration of classification model names."""
    LLM = "LLM"
    Ollama_LLM = "Ollama LLM"
    BGE_BASE = "BGE Base"
    BGE_ADVANCED = "BGE Advanced"
    DEBERTA_BASE = "DeBERTa Base"
    QWEN_ADVANCED = "QWEN Advanced"
    QWEN_CANDIDATE = "QWEN Candidate"
    SVM = "SVM"
    OPENAI = "OpenAI"
    def __repr__(self):
        return self.value

_MODEL_REGISTRY = {
    ClassificationModelName.LLM: LLM,
    ClassificationModelName.Ollama_LLM: Ollama_LLM,
    ClassificationModelName.BGE_BASE: BGE_Base,
    ClassificationModelName.BGE_ADVANCED: BGE_Advanced,
    ClassificationModelName.DEBERTA_BASE: DeBERTa_Base,
    ClassificationModelName.QWEN_ADVANCED: QWEN_Advanced,
    ClassificationModelName.QWEN_CANDIDATE: QWEN_Candidate,
    ClassificationModelName.SVM: SVM,
    ClassificationModelName.OPENAI: OpenAIModel,
}

# Backward-compatible aliases so config JSONs written before the class renames
# (class_name "HF_LLM" / "QWEN_Unified") remain loadable via from_dict/from_json.
ClassificationModel._registry.setdefault("HF_LLM", LLM)
ClassificationModel._registry.setdefault("QWEN_Unified", SVM)

def get_model(model_class_name: ClassificationModelName, model_name: str, **kwargs) -> ClassificationModel:
    """Get model instance by name."""
    if model_class_name not in _MODEL_REGISTRY:
        raise ValueError(f"Model '{model_class_name}' is not registered.")
    model_class = _MODEL_REGISTRY[model_class_name]
    return model_class(model_name, **kwargs)

def get_model_from_config(config_path: str):
    """Get model instance from a JSON config file."""
    return ClassificationModel.from_json(config_path)