from __future__ import annotations

import logging
from typing import Optional

from nps_crawling.classification.categories.category import (
    ClassificationCategory,
    ClassificationProperty,
    ClassificationType,
    DataEntry,
)
from nps_crawling.classification.models.model import (
    NotSupportedError,
    NotTrainedError,
)
from nps_crawling.classification.models.qwen_candidate import QWEN_Candidate
from nps_crawling.config import Config

logger = logging.getLogger(__name__)

_NUMERIC_TYPES = (ClassificationType.FLOAT, ClassificationType.INTEGER)


class QWEN_Unified(QWEN_Candidate):
    """Qwen embeddings for every property type, one class.

    Routes each property of a category to the strategy that fits its type:

    - ``BOOLEAN`` — per-property linear SVMs on shared snippet embeddings
      (the ``QWEN_Advanced`` optimized path).
    - ``FLOAT`` / ``INTEGER`` — numeric candidate extraction + one multi-class
      SVM per category (the ``QWEN_Candidate`` path).

    Mixed categories are supported; each text is embedded at most once per
    strategy and results are merged per property. This class always uses the
    shared-instruction embedding path regardless of the ``optimized`` kwarg.

    Keyword arguments are those of :class:`QWEN_Candidate` /
    :class:`QWEN_Advanced` (``context_chars``, ``candidate_min`` /
    ``candidate_max``, ``max_length``).
    """

    def __init__(self, model_name: str, model_input: str = "", **kwargs):
        super().__init__(model_name, model_input, **kwargs)
        # Boolean SVMs of this class live in the same "shared" cache directory
        # as QWEN_Advanced(optimized=true) and are interchangeable with it.
        self.optimized = True

    @staticmethod
    def _split_properties(
        category: ClassificationCategory,
    ) -> tuple[list[ClassificationProperty], list[ClassificationProperty]]:
        booleans = [p for p in category.properties if p.type == ClassificationType.BOOLEAN]
        numerics = [p for p in category.properties if p.type in _NUMERIC_TYPES]
        return booleans, numerics

    def is_supported(self, category: ClassificationCategory) -> bool:
        if not category.properties:
            return False
        supported = (ClassificationType.BOOLEAN,) + _NUMERIC_TYPES
        return all(prop.type in supported for prop in category.properties)

    def is_trained(self, category: ClassificationCategory) -> bool:
        booleans, numerics = self._split_properties(category)
        if booleans and not self._svms_trained(category, booleans):
            return False
        if numerics and not self._classifier_path(category).exists():
            return False
        return True

    def classify_batch(
        self,
        texts: list[str],
        category: ClassificationCategory,
    ) -> list[list[DataEntry]]:
        if not self.is_supported(category):
            raise NotSupportedError(
                f"{self.__class__.__name__} supports boolean, float and integer "
                f"properties only."
            )
        if not self.is_trained(category):
            raise NotTrainedError(
                f"Models for {category.name} not found. Train the model first."
            )
        texts = ["" if text is None else str(text) for text in texts]
        booleans, numerics = self._split_properties(category)

        merged: list[dict[str, object]] = [{} for _ in texts]
        if booleans:
            for target, result in zip(
                merged, self._classify_boolean_batch(texts, category, booleans)
            ):
                target.update(result)
        if numerics:
            for target, result in zip(
                merged, self._classify_candidate_batch(texts, category, numerics)
            ):
                target.update(result)

        return [
            [
                DataEntry(column_name=prop.name, value=result[prop.name])
                for prop in category.properties
            ]
            for result in merged
        ]

    def train(
        self,
        category: ClassificationCategory,
        text_column: str = Config.CLASSIFICATION_FEW_SHOT_TEXT_COLUMN,
        test_size: Optional[float] = Config.CLASSIFICATION_GROUND_TRUTH_TEST_SIZE,
    ) -> None:
        if not self.is_supported(category):
            raise NotSupportedError(
                f"{self.__class__.__name__} supports boolean, float and integer "
                f"properties only."
            )
        train_df, texts = self._training_frame(category, text_column, test_size)
        booleans, numerics = self._split_properties(category)
        if booleans:
            self._train_boolean_svms(category, train_df, texts, booleans)
        if numerics:
            self._train_candidate_classifier(category, train_df, texts, numerics)
