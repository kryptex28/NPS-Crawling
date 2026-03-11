"""Module for classification models used in the NPS crawling project."""
import logging
from abc import ABC
from pathlib import Path

import joblib
from sentence_transformers import SentenceTransformer

from nps_crawling.config import Config
from nps_crawling.llm.llm_ollama import LLMOllama

log = logging.getLogger(__package__)


class ClassificationModel(ABC):
    """Abstract base class for classification models."""

    def classify(self, text: str) -> str:
        """Classify the given text and return the predicted label."""
        pass


class OllamaModel(ClassificationModel, Config):
    """Classification model using Ollama LLM."""
    def __init__(self):
        """Initialize OllamaModel with LLMOllama."""
        self.llm = LLMOllama(
            persona=self.OLLAMA_PERSONA,
            model="mistral",
            host="localhost",
            port=14000,
            temperature=0.0,
            top_p=1.0,
            top_k=1,
            num_predict=128,
            seed=42,
            repeat_penalty=1.0,
        )

    def classify(self, text: str) -> str:
        """Classify the given text using the Ollama LLM."""
        return self.llm.classify(text)


class SVMClassificationModel(ClassificationModel):
    """Classification model using SVM."""
    def __init__(self):
        """Initialize SVMClassificationModel by loading the embedding model and SVM pipeline."""
        # Load your pre-trained Emedding and SVM model
        BASE_DIR = Path(__file__).resolve().parent
        BGE_CACHE_DIR = BASE_DIR / "cache" / "bge-m3"
        if not BGE_CACHE_DIR.exists():
            BGE_CACHE_DIR.mkdir(parents=True, exist_ok=True)
            self.embedding_model = SentenceTransformer(
                'BAAI/bge-m3',
            )
            self.embedding_model.save(str(BGE_CACHE_DIR))
        else:
            self.embedding_model = SentenceTransformer(str(BGE_CACHE_DIR))

        SVM_CACHE_DIR = BASE_DIR / "cache" / "svm_pipeline.joblib"
        if not SVM_CACHE_DIR.exists():
            raise FileNotFoundError(
                f"SVM model cache file not found at {SVM_CACHE_DIR}."
                "Please ensure the model is trained and saved correctly.")

        self.svm_model = joblib.load(SVM_CACHE_DIR)

        LABEL_ENCODER_CACHE_DIR = BASE_DIR / "cache" / "label_encoder.joblib"
        if not LABEL_ENCODER_CACHE_DIR.exists():
            raise FileNotFoundError(
                f"Label encoder cache file not found at {LABEL_ENCODER_CACHE_DIR}."
                "Please ensure the label encoder is saved correctly.")
        self.label_encoder = joblib.load(LABEL_ENCODER_CACHE_DIR)

    def classify(self, text: str) -> str:
        """Classify the given text using the SVM model."""
        # Implement classification logic using the loaded SVM model
        embedding = self.embedding_model.encode([text])
        prediction = self.svm_model.predict(embedding)
        prediction_label = self.label_encoder.inverse_transform(prediction)
        return prediction_label[0]


_MODEL_MAP = {
    "Ollama": OllamaModel,
    "SVM": SVMClassificationModel,
}


def get_classification_model(model_name: str) -> ClassificationModel:
    """Factory function to get the classification model based on the model name."""
    model_class = _MODEL_MAP.get(model_name)
    if not model_class:
        raise ValueError(f"Model '{model_name}' not recognized. Available models: {list(_MODEL_MAP.keys())}")
    return model_class()
