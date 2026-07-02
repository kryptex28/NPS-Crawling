from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Optional

import pandas as pd
import torch
import torch.nn.functional as F
from torch.optim import AdamW
from transformers import DebertaV2Config, DebertaV2ForSequenceClassification, DebertaV2Tokenizer

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


def _series_to_multilabel_float(series: pd.Series) -> torch.Tensor:
    """Map a boolean / 0-1 column to float targets in ``{0.0, 1.0}``."""
    out = []
    for v in series.tolist():
        if pd.isna(v):
            out.append(0.0)
        elif isinstance(v, bool):
            out.append(1.0 if v else 0.0)
        elif isinstance(v, (int, float)):
            out.append(1.0 if float(v) != 0.0 else 0.0)
        else:
            s = str(v).strip().lower()
            if s in ("true", "1", "yes", "y"):
                out.append(1.0)
            elif s in ("false", "0", "no", "n", ""):
                out.append(0.0)
            else:
                try:
                    out.append(1.0 if float(s.replace(",", ".")) != 0.0 else 0.0)
                except ValueError:
                    out.append(0.0)
    return torch.tensor(out, dtype=torch.float32)


def _load_deberta_v2_config(config_path: Path) -> DebertaV2Config:
    """Load a DeBERTa v2 config while normalizing legacy multi-label settings."""
    with config_path.open(encoding="utf-8") as f:
        config_dict = json.load(f)
    if config_dict.get("problem_type") == "multi_label":
        config_dict["problem_type"] = "multi_label_classification"
    return DebertaV2Config.from_dict(config_dict)


class DeBERTa_Base(ClassificationModel):
    """DeBERTa with a single fine-tuned classification head (multi-label).

    All properties in a category must be :class:`ClassificationType.BOOLEAN`. The encoder
    shares weights across labels; the Hugging Face classifier head has ``num_labels``
    outputs with ``problem_type="multi_label"`` (sigmoid + BCE).

    Checkpoints are stored under :attr:`ClassificationModel.cache_dir` in one directory
    per trained category (see :meth:`_checkpoint_dir`).

    Optional keyword arguments (also persisted in ``kwargs``):

        train_epochs (int): default ``3``.
        train_batch_size (int): default ``8``.
        train_learning_rate (float): default ``2e-5``.
        train_max_length (int): default ``512``.
        train_weight_decay (float): default ``0.01``.
    """

    def __init__(self, model_name: str, model_input: str = "", **kwargs):
        super().__init__(model_name, model_input, **kwargs)
        self._device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self._tokenizer: Any = None
        self._model: Any = None
        self._loaded_category_id: Optional[str] = None

    def _train_kw(self) -> dict[str, Any]:
        return {
            "train_epochs": int(self.kwargs.get("train_epochs", 3)),
            "train_batch_size": int(self.kwargs.get("train_batch_size", 8)),
            "train_learning_rate": float(self.kwargs.get("train_learning_rate", 2e-5)),
            "train_max_length": int(self.kwargs.get("train_max_length", 512)),
            "train_weight_decay": float(self.kwargs.get("train_weight_decay", 0.01)),
        }

    def _checkpoint_dir(self, category: ClassificationCategory) -> Path:
        safe = "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in category.name)
        return Path(self.cache_dir) / f"deberta_mlc_{safe}_{category.stable_id[:16]}"

    def _metadata_path(self, category: ClassificationCategory) -> Path:
        return self._checkpoint_dir(category) / "head_training.json"

    def _write_metadata(self, category: ClassificationCategory) -> None:
        meta = {
            "base_model_name": self.model_name,
            "category_name": category.name,
            "category_stable_id": category.stable_id,
            "property_names": [p.name for p in category.properties],
        }
        self._metadata_path(category).parent.mkdir(parents=True, exist_ok=True)
        with self._metadata_path(category).open("w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2)

    def _read_metadata(self, category: ClassificationCategory) -> dict[str, Any]:
        path = self._metadata_path(category)
        if not path.is_file():
            raise NotTrainedError(f"No DeBERTa head metadata at {path}. Train the model first.")
        with path.open(encoding="utf-8") as f:
            return json.load(f)

    def _validate_category(self, category: ClassificationCategory) -> None:
        for p in category.properties:
            if p.type != ClassificationType.BOOLEAN:
                raise NotSupportedError(
                    "DeBERTa_Base multi-label head only supports boolean properties; "
                    f"property {p.name!r} has type {p.type!r}."
                )

    def _assert_metadata_matches(self, meta: dict[str, Any], category: ClassificationCategory) -> None:
        if meta.get("category_stable_id") != category.stable_id:
            raise NotTrainedError(
                "Saved DeBERTa head was trained for a different category definition "
                f"(stable_id mismatch). Path: {self._checkpoint_dir(category)}"
            )
        names = meta.get("property_names") or []
        expected = [p.name for p in category.properties]
        if names != expected:
            raise NotTrainedError(
                f"Saved head property order {names!r} does not match current category {expected!r}."
            )

    def _load_head_for_category(self, category: ClassificationCategory) -> None:
        self._validate_category(category)
        ckpt = self._checkpoint_dir(category)
        cfg = ckpt / "config.json"
        if not cfg.is_file():
            raise NotTrainedError(
                f"No DeBERTa sequence-classification checkpoint at {ckpt}. Train the model first."
            )
        meta = self._read_metadata(category)
        self._assert_metadata_matches(meta, category)

        if self._loaded_category_id == category.stable_id and self._model is not None:
            return

        config = _load_deberta_v2_config(cfg)
        self._tokenizer = DebertaV2Tokenizer.from_pretrained(str(ckpt))
        self._model = DebertaV2ForSequenceClassification.from_pretrained(
            str(ckpt),
            config=config,
        )
        self._model.to(self._device)
        self._model.eval()
        self._loaded_category_id = category.stable_id

    def classify(self, text: str, category: ClassificationCategory) -> list[DataEntry]:
        return self.classify_batch([text], category)[0]

    def classify_batch(
        self,
        texts: list[str],
        category: ClassificationCategory,
    ) -> list[list[DataEntry]]:
        self._load_head_for_category(category)
        assert self._tokenizer is not None and self._model is not None
        tw = self._train_kw()
        batch_size = Config.CLASSIFICATION_EMBEDDING_BATCH_SIZE
        results: list[list[DataEntry]] = []
        for start in range(0, len(texts), batch_size):
            batch = texts[start : start + batch_size]
            enc = self._tokenizer(
                batch,
                padding=True,
                truncation=True,
                max_length=tw["train_max_length"],
                return_tensors="pt",
            )
            enc = {k: v.to(self._device) for k, v in enc.items()}
            with torch.inference_mode():
                logits = self._model(**enc).logits
                probs = torch.sigmoid(logits).cpu()
            for row in (probs >= 0.5).tolist():
                results.append(
                    [
                        DataEntry(column_name=p.name, value=bool(row[i]))
                        for i, p in enumerate(category.properties)
                    ]
                )
        return results

    def train(
        self,
        category: ClassificationCategory,
        text_column: str = Config.CLASSIFICATION_FEW_SHOT_TEXT_COLUMN,
        test_size: Optional[float] = Config.CLASSIFICATION_GROUND_TRUTH_TEST_SIZE,
    ) -> None:
        if not category.csv_path:
            raise ValueError("No csv as groundtruth provided")

        self._validate_category(category)

        df = pd.read_csv(resolved_category_csv_path(category.csv_path))
        train_df, _test_df = ground_truth_train_test_split(df, test_size=test_size)
        train_df = train_df.dropna(subset=[text_column])
        train_df = train_df[train_df[text_column].astype(str).str.strip() != ""]
        for p in category.properties:
            train_df = train_df[train_df[p.name].notna()]

        texts = train_df[text_column].astype(str).tolist()
        if not texts:
            raise ValueError("No training rows left after filtering.")

        n_labels = len(category.properties)
        label_cols = torch.stack(
            [_series_to_multilabel_float(train_df[p.name]) for p in category.properties],
            dim=1,
        )

        tw = self._train_kw()
        tokenizer = DebertaV2Tokenizer.from_pretrained(
            self.model_name,
            cache_dir=self.cache_dir,
        )
        model = DebertaV2ForSequenceClassification.from_pretrained(
            self.model_name,
            num_labels=n_labels,
            problem_type="multi_label_classification",
            cache_dir=self.cache_dir,
        )
        model.to(self._device)
        model.train()

        optimizer = AdamW(
            model.parameters(),
            lr=tw["train_learning_rate"],
            weight_decay=tw["train_weight_decay"],
        )

        n = len(texts)
        epochs = tw["train_epochs"]
        bs = tw["train_batch_size"]
        max_len = tw["train_max_length"]

        for epoch in range(epochs):
            running = 0.0
            steps = 0
            gen = torch.Generator()
            gen.manual_seed(Config.CLASSIFICATION_RANDOM_SEED + epoch)
            perm = torch.randperm(n, generator=gen)
            for start in range(0, n, bs):
                idx = perm[start : start + bs]
                batch_texts = [texts[i] for i in idx.tolist()]
                batch_labels = label_cols[idx].to(self._device).float()

                enc = tokenizer(
                    batch_texts,
                    padding=True,
                    truncation=True,
                    max_length=max_len,
                    return_tensors="pt",
                )
                enc = {k: v.to(self._device) for k, v in enc.items()}
                optimizer.zero_grad()
                out = model(**enc, labels=batch_labels)
                loss = out.loss
                if loss is None:
                    loss = F.binary_cross_entropy_with_logits(
                        out.logits,
                        batch_labels,
                    )
                loss.backward()
                optimizer.step()
                running += float(loss.detach().cpu())
                steps += 1
            if steps:
                logger.info("DeBERTa_Base epoch %s/%s mean loss %.4f", epoch + 1, epochs, running / steps)

        ckpt = self._checkpoint_dir(category)
        ckpt.mkdir(parents=True, exist_ok=True)
        model.save_pretrained(str(ckpt))
        tokenizer.save_pretrained(str(ckpt))
        self._write_metadata(category)

        self._tokenizer = tokenizer
        self._model = model
        self._model.eval()
        self._loaded_category_id = category.stable_id
