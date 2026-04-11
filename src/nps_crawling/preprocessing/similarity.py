"""Pipeline to score context windows via semantic similarity against a reference NPS description."""

import logging

# silence errors
import transformers

transformers.utils.logging.set_verbosity_error()
logging.getLogger("huggingface_hub").setLevel(logging.ERROR)

import numpy as np
from langchain_huggingface import HuggingFaceEmbeddings

from nps_crawling.config import Config

logger = logging.getLogger(__name__)


def _detect_device():
    """Return the best available torch device string."""
    try:
        import torch
        if torch.cuda.is_available():
            return "cuda"
    except ImportError:
        pass
    return "cpu"


class SimilarityPipeline:
    """Scores each context window by cosine similarity to a reference NPS text.

    Embeds the reference text once at init time.  For every record that has
    context windows, each window is embedded and compared.

    Decision logic
    --------------
    1. Every context window receives a ``similarity_score``.
    2. The records are split into two parallel collections: accepted and rejected.
    3. Contexts with ``similarity_score >= SIMILARITY_THRESHOLD_CONTEXT_WINDOW``
       are placed into the accepted output (to go to ``json_processed/``).
    4. Contexts falling below the threshold are placed into the rejected output
       (to go to ``json_reject/``) for auditing.
    """

    def __init__(self):
        """Initialize embedding model and pre-compute the reference embedding."""
        device = _detect_device()
        batch_size = 512 if device == "cuda" else 64

        logger.info(
            "Loading embedding model '%s' on %s (batch_size=%d) …",
            Config.SIMILARITY_EMBEDDING_MODEL, device, batch_size,
        )
        self.embeddings = HuggingFaceEmbeddings(
            model_name=Config.SIMILARITY_EMBEDDING_MODEL,
            model_kwargs={"device": device},
            encode_kwargs={"batch_size": batch_size},
        )
        self.reference_embedding = np.array(
            self.embeddings.embed_query(Config.SIMILARITY_REFERENCE_TEXT),
        )
        self.threshold_context = Config.SIMILARITY_THRESHOLD_CONTEXT_WINDOW
        logger.info(
            "Similarity pipeline ready (device=%s, window threshold=%.2f)",
            device, self.threshold_context,
        )

    # ------------------------------------------------------------------
    # Public helpers used by the chunked pipeline in utils.py
    # ------------------------------------------------------------------

    def embed_and_score(self, texts):
        """Embed a list of texts and return cosine similarity scores vs. reference.

        Args:
            texts: list of strings to embed.

        Returns:
            np.ndarray of float scores, one per input text.
        """
        if not texts:
            return np.array([])
        all_embeddings = np.array(self.embeddings.embed_documents(texts))
        norms = np.linalg.norm(all_embeddings, axis=1)
        ref_norm = np.linalg.norm(self.reference_embedding)
        dots = all_embeddings @ self.reference_embedding
        safe_divisor = norms * ref_norm
        safe_divisor[safe_divisor == 0] = 1.0
        return dots / safe_divisor

    def compute_record_metadata(self, records):
        """Compute per-record accept/reject counts and filing average.

        Expects ``similarity_score`` to already be set on each context dict.
        """
        for record in records:
            contexts = record.get("context", [])
            if not contexts:
                continue
            scores = [ctx["similarity_score"] for ctx in contexts]
            accepted_count = sum(1 for s in scores if s >= self.threshold_context)
            record["metadata"]["Context Windows Accept"] = accepted_count
            record["metadata"]["Context Windows Reject"] = len(scores) - accepted_count
            record["filings_average"] = round(float(sum(scores) / len(scores)), 4)

    def split_records(self, records):
        """Split records into accepted and rejected lists without deep-copying.

        Creates lightweight shallow copies that share immutable data but have
        independent ``context`` lists and ``metadata`` dicts so downstream
        mutations (e.g. popping ``core_text``) don't cross-contaminate.

        Returns:
            tuple[list, list]: (accepted_records, rejected_records)
        """
        accepted_records = []
        rejected_records = []

        for record in records:
            contexts = record.get("context", [])

            acc_ctx = [
                ctx for ctx in contexts
                if ctx.get("similarity_score", 0) >= self.threshold_context
            ]
            rej_ctx = [
                ctx for ctx in contexts
                if ctx.get("similarity_score", 0) < self.threshold_context
            ]

            # Shallow copy the record, give each branch its own metadata dict
            # and its own context list.  All other values (strings, ints) are
            # immutable and safe to share.
            acc_record = {**record, "metadata": record.get("metadata", {}).copy(), "context": acc_ctx}
            rej_record = {**record, "metadata": record.get("metadata", {}).copy(), "context": rej_ctx}

            accepted_records.append(acc_record)
            rejected_records.append(rej_record)

        return accepted_records, rejected_records

    # ------------------------------------------------------------------
    # Legacy all-in-one interface (kept for backward compatibility)
    # ------------------------------------------------------------------

    def similarity_workflow(self, records):
        """Score every context window and split based on threshold.

        Args:
            records: list of dicts, each with optional ``context`` list.

        Returns:
            tuple[list, list]:
                - *accepted_records*: records with context windows >= threshold.
                - *rejected_records*: records with context windows < threshold.
        """
        # Collect all context texts for a single batched embedding call.
        all_texts = []
        index_map = []  # (record_index, context_index)
        for rec_idx, record in enumerate(records):
            contexts = record.get("context", [])
            if "metadata" not in record:
                record["metadata"] = {}
            record["metadata"]["experiment"] = Config.PREPROCESSING_VERSION
            record["metadata"]["Context Windows total"] = len(contexts)
            if not contexts:
                record["metadata"]["Context Windows Accept"] = 0
                record["metadata"]["Context Windows Reject"] = 0
                continue
            for ctx_idx, ctx in enumerate(contexts):
                all_texts.append(ctx["context"])
                index_map.append((rec_idx, ctx_idx))

        # Batch-embed and assign scores
        if all_texts:
            all_scores = self.embed_and_score(all_texts)
            for i, (rec_idx, ctx_idx) in enumerate(index_map):
                records[rec_idx]["context"][ctx_idx]["similarity_score"] = round(
                    float(all_scores[i]), 4,
                )

        self.compute_record_metadata(records)
        return self.split_records(records)
