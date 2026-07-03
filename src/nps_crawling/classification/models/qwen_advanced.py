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
import torch.nn.functional as F
from torch import Tensor
from transformers import AutoModel, AutoTokenizer

from nps_crawling.classification.categories.category import (
    ClassificationCategory,
    ClassificationProperty,
    ClassificationType,
    DataEntry,
)
from nps_crawling.classification.models.model import (
    ClassificationModel,
    NotSupportedError,
    NotTrainedError,
    ground_truth_train_test_split,
    resolved_category_csv_path,
)
from nps_crawling.config import Config

logger = logging.getLogger(__name__)


def _kwarg_flag(value: object) -> bool:
    return str(value).strip().lower() in ("1", "true", "yes")


class QWEN_Advanced(ClassificationModel):
    """Qwen embedding model + per-property linear SVMs.

    Optional keyword arguments (persisted in ``kwargs`` / the config hash):

        optimized (bool-ish): embed each text once per batch with a shared
            instruction and reuse that embedding for every property SVM,
            instead of re-embedding per property. SVMs for this variant are
            cached under a separate ``shared`` directory.
        max_length (int): tokenizer truncation length, default ``1024``.
    """

    # Shared instruction for the optimized variant: one embedding per text,
    # reused across all properties (and categories, via the batch memo).
    SHARED_INSTRUCTION = (
        "Classify a snippet from an SEC filing with respect to how it reports "
        "Net Promoter Score (NPS)."
    )

    def __init__(self, model_name: str, model_input: str = "", **kwargs):
        super().__init__(model_name, model_input, **kwargs)
        self.optimized = _kwarg_flag(kwargs.get("optimized", False))
        self.max_length = int(kwargs.get("max_length", 1024))
        self.tokenizer = AutoTokenizer.from_pretrained(
            model_name, cache_dir=self.cache_dir, padding_side="left"
        )
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        dtype = torch.float16 if self.device.type == "cuda" else torch.float32
        self.model = AutoModel.from_pretrained(
            model_name, cache_dir=self.cache_dir, torch_dtype=dtype
        ).to(self.device)
        self.model.eval()
        self._svm_cache: dict[Path, object] = {}
        # Memo of recently embedded batches keyed by (instruction, texts) hash.
        # With a shared instruction the same texts produce the same embeddings
        # for every category, so consecutive per-category calls reuse one
        # forward pass. Kept small: batches can be large.
        self._embed_memo: dict[int, np.ndarray] = {}

    @staticmethod
    def _last_token_pool(last_hidden_states: Tensor, attention_mask: Tensor) -> Tensor:
        left_padding = attention_mask[:, -1].sum() == attention_mask.shape[0]
        if left_padding:
            return last_hidden_states[:, -1]
        sequence_lengths = attention_mask.sum(dim=1) - 1
        batch_size = last_hidden_states.shape[0]
        return last_hidden_states[
            torch.arange(batch_size, device=last_hidden_states.device),
            sequence_lengths,
        ]

    @staticmethod
    def _format_instruction(task_description: str, text: str) -> str:
        return f"Instruct: {task_description}\nQuery: {text}"

    def _get_instruction(self, classification_property: ClassificationProperty) -> str:
        desc = (classification_property.description or "").strip()
        if desc:
            return f"Represent the text for classification: {desc}"
        return "Represent the text for classification."

    def _embed_texts(
        self,
        texts: list[str],
        instruction: str,
    ) -> np.ndarray:
        """Embed all texts for one instruction, batched on the model device.

        Texts are processed in length-sorted order so batches pad to similar
        lengths; the returned array is in the original order.
        """
        formatted_texts = [self._format_instruction(instruction, text) for text in texts]
        order = sorted(range(len(formatted_texts)), key=lambda i: len(formatted_texts[i]))

        batch_size = Config.CLASSIFICATION_EMBEDDING_BATCH_SIZE
        embeddings = []
        for start in range(0, len(order), batch_size):
            batch = [formatted_texts[i] for i in order[start : start + batch_size]]
            encoded_input = self.tokenizer(
                batch,
                padding=True,
                truncation=True,
                max_length=self.max_length,
                return_tensors="pt",
            ).to(self.device)

            with torch.inference_mode():
                model_output = self.model(**encoded_input)
                sentence_embeddings = self._last_token_pool(
                    model_output.last_hidden_state,
                    encoded_input["attention_mask"],
                )

            sentence_embeddings = F.normalize(sentence_embeddings, p=2, dim=1)
            embeddings.append(sentence_embeddings.float().cpu().numpy())

        stacked = np.vstack(embeddings)
        result = np.empty_like(stacked)
        result[np.asarray(order)] = stacked
        return result

    def _embed_texts_memoized(self, texts: list[str], instruction: str) -> np.ndarray:
        key = hash((instruction, tuple(texts)))
        if key in self._embed_memo:
            return self._embed_memo[key]
        embeddings = self._embed_texts(texts, instruction)
        if len(self._embed_memo) >= 4:
            self._embed_memo.pop(next(iter(self._embed_memo)))
        self._embed_memo[key] = embeddings
        return embeddings

    def _get_embedding(self, text: str, classification_property: ClassificationProperty):
        return self._embed_texts([text], self._get_instruction(classification_property))[0]

    def _svm_path(self, category: ClassificationCategory, class_property: ClassificationProperty) -> Path:
        base = Path(self.cache_dir) / self.model_name.split("/")[-1]
        if self.optimized:
            return base / "shared" / f"{class_property.name}.joblib"
        return base / f"{class_property.name}.joblib"

    def _load_svm(self, category: ClassificationCategory, class_property: ClassificationProperty):
        svm_path = self._svm_path(category, class_property)
        if svm_path not in self._svm_cache:
            self._svm_cache[svm_path] = joblib.load(svm_path)
        return self._svm_cache[svm_path]

    def is_supported(self, category: ClassificationCategory) -> bool:
        for property in category.properties:
            if not property.type == ClassificationType.BOOLEAN:
                return False
        return True

    def _svms_trained(
        self,
        category: ClassificationCategory,
        properties: list[ClassificationProperty],
    ) -> bool:
        for property in properties:
            svm_path = self._svm_path(category, property)
            if not svm_path.exists():
                return False
        return True

    def is_trained(self, category: ClassificationCategory) -> bool:
        return self._svms_trained(category, category.properties)

    @staticmethod
    def _training_frame(
        category: ClassificationCategory,
        text_column: str,
        test_size: Optional[float],
    ) -> tuple[pd.DataFrame, list[str]]:
        """Load the training fold of the category's ground-truth CSV."""
        if not category.csv_path:
            raise ValueError("No csv as groundtruth provided")
        df = pd.read_csv(resolved_category_csv_path(category.csv_path))
        train_df, _test_df = ground_truth_train_test_split(df, test_size=test_size)
        train_df = train_df.dropna(subset=[text_column])
        train_df = train_df[train_df[text_column].astype(str).str.strip() != ""]
        return train_df, train_df[text_column].astype(str).tolist()

    def classify(self, text: str, category: ClassificationCategory) -> list[DataEntry]:
        return self.classify_batch([text], category)[0]

    def _classify_boolean_batch(
        self,
        texts: list[str],
        category: ClassificationCategory,
        properties: list[ClassificationProperty],
    ) -> list[dict[str, int]]:
        """Predict the boolean ``properties`` for every text via per-property SVMs."""
        results: list[dict[str, int]] = [{} for _ in texts]
        shared_embeddings: Optional[np.ndarray] = None
        if self.optimized:
            shared_embeddings = self._embed_texts_memoized(texts, self.SHARED_INSTRUCTION)
        for class_property in properties:
            svm_model = self._load_svm(category, class_property)
            if shared_embeddings is not None:
                embeddings = shared_embeddings
            else:
                embeddings = self._embed_texts(texts, self._get_instruction(class_property))
            predictions = svm_model.predict(embeddings)
            for result, prediction in zip(results, predictions):
                result[class_property.name] = int(prediction)
            logger.info(
                f"{self.model_name}: {category.name}/{class_property.name} "
                f"classified {len(texts)} texts"
            )
        return results

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
        results = self._classify_boolean_batch(texts, category, category.properties)
        return [
            [
                DataEntry(column_name=prop.name, value=result[prop.name])
                for prop in category.properties
            ]
            for result in results
        ]

    def _train_boolean_svms(
        self,
        category: ClassificationCategory,
        train_df: pd.DataFrame,
        texts: list[str],
        properties: list[ClassificationProperty],
    ) -> None:
        shared_embeddings: Optional[np.ndarray] = None
        if self.optimized:
            shared_embeddings = self._embed_texts_memoized(texts, self.SHARED_INSTRUCTION)

        for class_property in properties:
            if shared_embeddings is not None:
                labels_series = train_df[class_property.name]
                mask = labels_series.notna().to_numpy()
                embeddings = shared_embeddings[mask]
                labels = labels_series[labels_series.notna()].tolist()
            else:
                embeddings = self._embed_texts(texts, self._get_instruction(class_property))
                labels = train_df[class_property.name].tolist()
            svm_model = make_pipeline(
                StandardScaler(),
                SVC(kernel="linear", random_state=Config.CLASSIFICATION_RANDOM_SEED),
            )
            svm_model.fit(embeddings, labels)
            svm_path = self._svm_path(category, class_property)
            svm_path.parent.mkdir(parents=True, exist_ok=True)
            joblib.dump(svm_model, svm_path)
            self._svm_cache[svm_path] = svm_model

    def train(
        self,
        category: ClassificationCategory,
        text_column: str = Config.CLASSIFICATION_FEW_SHOT_TEXT_COLUMN,
        test_size: Optional[float] = Config.CLASSIFICATION_GROUND_TRUTH_TEST_SIZE,
    ) -> None:
        if not self.is_supported(category):
            raise NotSupportedError(
                "SVM models are only supported for boolean classification."
            )
        train_df, texts = self._training_frame(category, text_column, test_size)
        self._train_boolean_svms(category, train_df, texts, category.properties)
