from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
import torch

from nps_crawling.classification.categories.category import (
    ClassificationCategory,
    ClassificationProperty,
)
from nps_crawling.classification.models.svm import SVM
from nps_crawling.config import Config

logger = logging.getLogger(__name__)


class BGE_SVM(SVM):
    """Unified SVM pipeline on native BGE embeddings.

    Same property routing as :class:`SVM` (``BOOLEAN`` properties via shared
    per-property linear SVMs, ``FLOAT`` / ``INTEGER`` via numeric candidate
    classification), but embeds text the way BGE models are trained to be
    used: no instruction prefix, right padding, CLS-token pooling. The Qwen
    path's instruction prompts and last-token pooling measurably degrade BGE
    backbones, so every instruction argument is ignored here.

    Cache artifacts live under ``<cache>/<model>/bge_native/`` so they never
    collide with SVMs trained by the Qwen-style classes on the same backbone.
    """

    def __init__(self, model_name: str, model_input: str = "", **kwargs):
        super().__init__(model_name, model_input, **kwargs)
        # CLS pooling reads position 0; left padding would put a PAD token there.
        self.tokenizer.padding_side = "right"

    def _base_dir(self) -> Path:
        return Path(self.cache_dir) / self.model_name.split("/")[-1] / "bge_native"

    def _svm_path(
        self, category: ClassificationCategory, class_property: ClassificationProperty
    ) -> Path:
        return self._base_dir() / "shared" / f"{class_property.name}.joblib"

    def _classifier_path(self, category: ClassificationCategory) -> Path:
        safe = "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in category.name)
        return self._base_dir() / "candidates" / f"{safe}_{category.stable_id[:16]}.joblib"

    def _embed_texts(self, texts: list[str], instruction: str) -> np.ndarray:
        """Embed the raw texts; ``instruction`` is intentionally unused.

        Texts are processed in length-sorted order so batches pad to similar
        lengths; the returned array is in the original order.
        """
        order = sorted(range(len(texts)), key=lambda i: len(texts[i]))
        batch_size = Config.CLASSIFICATION_EMBEDDING_BATCH_SIZE
        embeddings = []
        for start in range(0, len(order), batch_size):
            batch = [texts[i] for i in order[start : start + batch_size]]
            encoded_input = self.tokenizer(
                batch,
                padding=True,
                truncation=True,
                max_length=self.max_length,
                return_tensors="pt",
            ).to(self.device)
            with torch.inference_mode():
                model_output = self.model(**encoded_input)
                sentence_embeddings = model_output.last_hidden_state[:, 0]
            sentence_embeddings = torch.nn.functional.normalize(sentence_embeddings, p=2, dim=1)
            embeddings.append(sentence_embeddings.float().cpu().numpy())

        stacked = np.vstack(embeddings)
        result = np.empty_like(stacked)
        result[np.asarray(order)] = stacked
        return result
