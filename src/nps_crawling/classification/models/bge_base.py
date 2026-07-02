from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import joblib
import numpy as np
import pandas as pd
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC
import torch
from transformers import AutoModel, AutoTokenizer

from nps_crawling.classification.categories.category import ClassificationCategory, ClassificationType, DataEntry
from nps_crawling.classification.models.model import (
    ClassificationModel,
    NotSupportedError,
    NotTrainedError,
    ground_truth_train_test_split,
    resolved_category_csv_path,
)
from nps_crawling.config import Config

logger = logging.getLogger(__name__)


class BGE_Base(ClassificationModel):
    """BGE embedding (shared) + per-property linear SVMs."""

    def __init__(self, model_name: str, model_input: str = "", **kwargs):
        super().__init__(model_name, model_input, **kwargs)
        self.tokenizer = AutoTokenizer.from_pretrained(model_name, cache_dir=self.cache_dir)
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        dtype = torch.float16 if self.device.type == "cuda" else torch.float32
        self.model = AutoModel.from_pretrained(
            model_name, cache_dir=self.cache_dir, torch_dtype=dtype
        ).to(self.device)
        self.model.eval()
        self._svm_cache: dict[Path, object] = {}

    def _embed_texts(self, texts: list[str]) -> np.ndarray:
        """Embed all texts (shared across properties), batched on the model device."""
        batch_size = Config.CLASSIFICATION_EMBEDDING_BATCH_SIZE
        embeddings = []
        for start in range(0, len(texts), batch_size):
            batch = texts[start : start + batch_size]
            encoded_input = self.tokenizer(
                batch,
                padding=True,
                truncation=True,
                return_tensors="pt",
            ).to(self.device)
            with torch.no_grad():
                model_output = self.model(**encoded_input)
                sentence_embeddings = model_output[0][:, 0]
            sentence_embeddings = torch.nn.functional.normalize(sentence_embeddings, p=2, dim=1)
            embeddings.append(sentence_embeddings.float().cpu().numpy())

        return np.vstack(embeddings)

    def _get_embedding(self, text: str):
        return self._embed_texts([text])[0]

    def _svm_path(self, category: ClassificationCategory, class_property) -> Path:
        return Path(self.cache_dir) / self.model_name.split("/")[-1] / f"{category.name}_{class_property.name}.joblib"

    def _load_svm(self, category: ClassificationCategory, class_property):
        svm_path = self._svm_path(category, class_property)
        if svm_path not in self._svm_cache:
            self._svm_cache[svm_path] = joblib.load(svm_path)
        return self._svm_cache[svm_path]

    def is_supported(self, category: ClassificationCategory) -> bool:
        for property in category.properties:
            if not property.type == ClassificationType.BOOLEAN:
                return False
        return True

    def is_trained(self, category: ClassificationCategory) -> bool:
        for property in category.properties:
            svm_path = self._svm_path(category, property)
            if not svm_path.exists():
                return False
        return True

    def classify(self, text: str, category: ClassificationCategory) -> list[DataEntry]:
        return self.classify_batch([text], category)[0]

    def classify_batch(
        self,
        texts: list[str],
        category: ClassificationCategory,
    ) -> list[list[DataEntry]]:
        if not self.is_supported(category):
            raise NotSupportedError(
                "SVM models are only supported for boolean classification."
            )
        if not self.is_trained(category):
            raise NotTrainedError(
                f"SVM models for {category.name} not found. Train the model first."
            )
        embeddings = self._embed_texts(texts)
        data_entries: list[list[DataEntry]] = [[] for _ in texts]
        for class_property in category.properties:
            svm_model = self._load_svm(category, class_property)
            predictions = svm_model.predict(embeddings)
            for entries, prediction in zip(data_entries, predictions):
                entries.append(DataEntry(column_name=class_property.name, value=int(prediction)))
        logger.info(f"{self.model_name}: {category.name} classified {len(texts)} texts")

        return data_entries

    def train(
        self,
        category: ClassificationCategory,
        text_column: str = Config.CLASSIFICATION_FEW_SHOT_TEXT_COLUMN,
        test_size: Optional[float] = Config.CLASSIFICATION_GROUND_TRUTH_TEST_SIZE,
    ) -> None:
        if not category.csv_path:
            raise ValueError("No csv as groundtruth provided")
        if not self.is_supported(category):
            raise NotSupportedError(
                "SVM models are only supported for boolean classification."
            )
        df = pd.read_csv(resolved_category_csv_path(category.csv_path))
        train_df, _test_df = ground_truth_train_test_split(df, test_size=test_size)
        train_df = train_df.dropna(subset=[text_column])
        train_df = train_df[train_df[text_column].astype(str).str.strip() != ""]
        texts = train_df[text_column].tolist()

        shared_embeddings = self._embed_texts(texts)

        for class_property in category.properties:
            if not class_property.type == ClassificationType.BOOLEAN:
                raise NotSupportedError(
                    "SVM models are only supported for boolean classification."
                )
            labels = train_df[class_property.name].tolist()
            svm_model = make_pipeline(
                StandardScaler(),
                SVC(kernel="linear", random_state=Config.CLASSIFICATION_RANDOM_SEED),
            )
            svm_model.fit(shared_embeddings, labels)
            svm_path = self._svm_path(category, class_property)
            svm_path.parent.mkdir(parents=True, exist_ok=True)
            joblib.dump(svm_model, svm_path)
            self._svm_cache[svm_path] = svm_model
