from __future__ import annotations

import logging
import math
import re
from pathlib import Path
from typing import Optional

import joblib
import pandas as pd
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC

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
from nps_crawling.classification.models.qwen_advanced import QWEN_Advanced
from nps_crawling.config import Config

logger = logging.getLogger(__name__)

# Standalone numbers up to 3 integer digits with optional sign and decimals.
# Skips digits inside words (Q4), decimals tails (the 5 in 3.5), thousands
# groups (12,000) and 4+ digit numbers such as years.
_NUMBER_PATTERN = re.compile(r"(?<![\w.,])[-+]?\d{1,3}(?:\.\d+)?(?!\d|,\d{3}|\.\d)")


class QWEN_Candidate(QWEN_Advanced):
    """Numeric value extraction as candidate classification.

    Supports categories whose properties are all :attr:`ClassificationType.FLOAT`
    or :attr:`ClassificationType.INTEGER`. Every standalone number in a text is a
    candidate; each candidate is embedded in a marked local context window and a
    single multi-class SVM per category assigns it one of the property names or
    ``NONE_LABEL``. Per property, the highest-confidence candidate provides the
    predicted value; properties without a candidate get their default value.

    Training data comes from the category's ground-truth CSV: a candidate is a
    positive example for the first property whose cell value matches it, all
    other candidates are negatives. This requires the true values to appear
    verbatim in the text, which holds for value-extraction style properties.

    Optional keyword arguments (persisted in ``kwargs`` / the config hash):

        context_chars (int): characters kept on each side of a candidate when
            building its context window, default ``240``.
        candidate_min / candidate_max (float): inclusive value range filter for
            candidates, default unbounded (the pattern itself allows at most
            three integer digits).
        max_length (int): tokenizer truncation length (see
            :class:`QWEN_Advanced`), default ``1024``.
    """

    NONE_LABEL = "__none__"
    CANDIDATE_INSTRUCTION = (
        "Identify the role of the numeric value enclosed in « » "
        "within the surrounding text."
    )

    def __init__(self, model_name: str, model_input: str = "", **kwargs):
        super().__init__(model_name, model_input, **kwargs)
        self.context_chars = int(kwargs.get("context_chars", 240))
        self.candidate_min = float(kwargs["candidate_min"]) if "candidate_min" in kwargs else None
        self.candidate_max = float(kwargs["candidate_max"]) if "candidate_max" in kwargs else None

    # --- candidate extraction -------------------------------------------------

    def _extract_candidates(self, text: str) -> list[tuple[float, int, int]]:
        """Return ``(value, start, end)`` for every candidate number in ``text``."""
        candidates = []
        for match in _NUMBER_PATTERN.finditer(text):
            try:
                value = float(match.group())
            except ValueError:
                continue
            if self.candidate_min is not None and value < self.candidate_min:
                continue
            if self.candidate_max is not None and value > self.candidate_max:
                continue
            candidates.append((value, match.start(), match.end()))
        return candidates

    def _candidate_context(self, text: str, start: int, end: int) -> str:
        window_start = max(0, start - self.context_chars)
        window_end = min(len(text), end + self.context_chars)
        return (
            text[window_start:start]
            + "«"
            + text[start:end]
            + "»"
            + text[end:window_end]
        )

    def _candidate_dataset(
        self, texts: list[str]
    ) -> tuple[list[str], list[int], list[float]]:
        """Extract candidates from all texts.

        Returns parallel lists: context windows, owning text index, numeric value.
        """
        contexts: list[str] = []
        owners: list[int] = []
        values: list[float] = []
        for i, text in enumerate(texts):
            for value, start, end in self._extract_candidates(text):
                contexts.append(self._candidate_context(text, start, end))
                owners.append(i)
                values.append(value)
        return contexts, owners, values

    # --- persistence ----------------------------------------------------------

    def _classifier_path(self, category: ClassificationCategory) -> Path:
        safe = "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in category.name)
        return (
            Path(self.cache_dir)
            / self.model_name.split("/")[-1]
            / "candidates"
            / f"{safe}_{category.stable_id[:16]}.joblib"
        )

    def _load_classifier(self, category: ClassificationCategory):
        path = self._classifier_path(category)
        if path not in self._svm_cache:
            self._svm_cache[path] = joblib.load(path)
        return self._svm_cache[path]

    # --- ClassificationModel interface ----------------------------------------

    def is_supported(self, category: ClassificationCategory) -> bool:
        if not category.properties:
            return False
        return all(
            prop.type in (ClassificationType.FLOAT, ClassificationType.INTEGER)
            for prop in category.properties
        )

    def is_trained(self, category: ClassificationCategory) -> bool:
        return self._classifier_path(category).exists()

    @staticmethod
    def _cast_candidate(value: float, prop: ClassificationProperty):
        return prop.cast_value(value)

    def _classify_candidate_batch(
        self,
        texts: list[str],
        category: ClassificationCategory,
        properties: list[ClassificationProperty],
    ) -> list[dict[str, object]]:
        """Predict the numeric ``properties`` for every text via candidate classification."""
        classifier = self._load_classifier(category)
        contexts, owners, values = self._candidate_dataset(texts)

        results: list[dict[str, object]] = [
            {prop.name: prop.default_value for prop in properties}
            for _ in texts
        ]
        if contexts:
            embeddings = self._embed_texts_memoized(contexts, self.CANDIDATE_INSTRUCTION)
            # Labels come from predict(), which honors class_weight; the Platt
            # probabilities are only used to rank candidates with the same
            # label (predict_proba's argmax reverts to the class priors and
            # almost always picks NONE_LABEL on this imbalanced data).
            predicted_labels = classifier.predict(embeddings)
            probabilities = classifier.predict_proba(embeddings)
            class_index = {label: i for i, label in enumerate(classifier.classes_)}
            property_names = {prop.name for prop in properties}
            # (text index, property) -> confidence of the winning candidate
            best_confidence: dict[tuple[int, str], float] = {}
            for label, row, owner, value in zip(predicted_labels, probabilities, owners, values):
                if label == self.NONE_LABEL or label not in property_names:
                    continue
                confidence = float(row[class_index[label]])
                key = (owner, label)
                if confidence > best_confidence.get(key, -1.0):
                    best_confidence[key] = confidence
                    prop = category.get_property(label)
                    results[owner][label] = self._cast_candidate(value, prop)
        logger.info(
            f"{self.model_name}: {category.name} classified {len(texts)} texts "
            f"({len(contexts)} numeric candidates)"
        )
        return results

    def classify_batch(
        self,
        texts: list[str],
        category: ClassificationCategory,
    ) -> list[list[DataEntry]]:
        if not self.is_supported(category):
            raise NotSupportedError(
                "Candidate models only support categories with float/integer properties."
            )
        if not self.is_trained(category):
            raise NotTrainedError(
                f"Candidate classifier for {category.name} not found. Train the model first."
            )
        texts = ["" if text is None else str(text) for text in texts]
        results = self._classify_candidate_batch(texts, category, category.properties)
        return [
            [
                DataEntry(column_name=prop.name, value=result[prop.name])
                for prop in category.properties
            ]
            for result in results
        ]

    def _train_candidate_classifier(
        self,
        category: ClassificationCategory,
        train_df: pd.DataFrame,
        texts: list[str],
        properties: list[ClassificationProperty],
    ) -> None:
        contexts, owners, values = self._candidate_dataset(texts)
        if not contexts:
            raise ValueError("No numeric candidates found in the training texts.")

        row_targets: list[dict[str, float]] = []
        for _, row in train_df.iterrows():
            targets = {}
            for prop in properties:
                cast = prop.cast_value(row[prop.name]) if prop.name in row.index else None
                if cast is not None:
                    targets[prop.name] = float(cast)
            row_targets.append(targets)

        labels = []
        for owner, value in zip(owners, values):
            label = self.NONE_LABEL
            for prop in properties:
                target = row_targets[owner].get(prop.name)
                if target is not None and math.isclose(value, target, abs_tol=1e-5):
                    label = prop.name
                    break
            labels.append(label)

        label_counts = pd.Series(labels).value_counts().to_dict()
        logger.info(
            f"{self.model_name}: training {category.name} candidate classifier on "
            f"{len(contexts)} candidates from {len(texts)} texts; labels: {label_counts}"
        )
        if len(set(labels)) < 2:
            raise ValueError(
                "Training candidates contain fewer than two classes; "
                "check that ground-truth values appear verbatim in the texts."
            )

        embeddings = self._embed_texts_memoized(contexts, self.CANDIDATE_INSTRUCTION)
        classifier = make_pipeline(
            StandardScaler(),
            SVC(
                kernel="rbf",
                probability=True,
                class_weight="balanced",
                random_state=Config.CLASSIFICATION_RANDOM_SEED,
            ),
        )
        classifier.fit(embeddings, labels)
        path = self._classifier_path(category)
        path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(classifier, path)
        self._svm_cache[path] = classifier

    def train(
        self,
        category: ClassificationCategory,
        text_column: str = Config.CLASSIFICATION_FEW_SHOT_TEXT_COLUMN,
        test_size: Optional[float] = Config.CLASSIFICATION_GROUND_TRUTH_TEST_SIZE,
    ) -> None:
        if not self.is_supported(category):
            raise NotSupportedError(
                "Candidate models only support categories with float/integer properties."
            )
        train_df, texts = self._training_frame(category, text_column, test_size)
        self._train_candidate_classifier(category, train_df, texts, category.properties)
