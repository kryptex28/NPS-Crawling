"""Pipeline to score context windows via semantic similarity against a reference NPS description."""

import copy
import logging

# silence errors
import transformers

transformers.utils.logging.set_verbosity_error()
logging.getLogger("huggingface_hub").setLevel(logging.ERROR)

import numpy as np
from langchain_huggingface import HuggingFaceEmbeddings

from nps_crawling.config import Config

logger = logging.getLogger(__name__)


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
        logger.info("Loading embedding model '%s' …", Config.SIMILARITY_EMBEDDING_MODEL)
        self.embeddings = HuggingFaceEmbeddings(model_name=Config.SIMILARITY_EMBEDDING_MODEL)
        self.reference_embedding = np.array(
            self.embeddings.embed_query(Config.SIMILARITY_REFERENCE_TEXT),
        )
        self.threshold_context = Config.SIMILARITY_THRESHOLD_CONTEXT_WINDOW
        logger.info(
            "Similarity pipeline ready (window threshold=%.2f)",
            self.threshold_context,
        )

    def similarity_workflow(self, records):
        """Score every context window and split based on threshold.

        Args:
            records: list of dicts, each with optional ``context`` list.

        Returns:
            tuple[list, list]:
                - *accepted_records*: records with context windows >= SIMILARITY_THRESHOLD_CONTEXT_WINDOW.
                - *rejected_records*: records with context windows < SIMILARITY_THRESHOLD_CONTEXT_WINDOW.
        """
        # Collect all context texts across all records for a single batched
        # embedding call, and track which record/context each text belongs to.
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

        # Batch-embed all context texts at once and compute cosine similarities
        # with vectorized numpy operations.
        if all_texts:
            all_embeddings = np.array(self.embeddings.embed_documents(all_texts))
            # Vectorized cosine similarity against the reference embedding
            norms = np.linalg.norm(all_embeddings, axis=1)
            ref_norm = np.linalg.norm(self.reference_embedding)
            dots = all_embeddings @ self.reference_embedding
            # Guard against zero norms
            safe_divisor = norms * ref_norm
            safe_divisor[safe_divisor == 0] = 1.0
            all_scores = dots / safe_divisor

            # Assign scores back to the original context dicts
            for i, (rec_idx, ctx_idx) in enumerate(index_map):
                records[rec_idx]["context"][ctx_idx]["similarity_score"] = round(
                    float(all_scores[i]), 4,
                )

        # Compute per-record metadata (accept/reject counts, filing average)
        for record in records:
            contexts = record.get("context", [])
            if not contexts:
                continue
            scores = [ctx["similarity_score"] for ctx in contexts]
            accepted_count = sum(1 for s in scores if s >= self.threshold_context)
            record["metadata"]["Context Windows Accept"] = accepted_count
            record["metadata"]["Context Windows Reject"] = len(scores) - accepted_count
            record["filings_average"] = round(float(sum(scores) / len(scores)), 4)

        # Build accepted and rejected record lists with a single deepcopy
        # instead of two, then filter context lists in place on each copy.
        accepted_records = copy.deepcopy(records)
        rejected_records = []
        for rec_acc in accepted_records:
            ctxs = rec_acc.get("context", [])
            if ctxs:
                rec_rej = copy.copy(rec_acc)
                rec_rej["metadata"] = rec_acc["metadata"].copy()
                rec_rej["context"] = [
                    ctx for ctx in ctxs
                    if ctx.get("similarity_score", 0) < self.threshold_context
                ]
                rec_acc["context"] = [
                    ctx for ctx in ctxs
                    if ctx.get("similarity_score", 0) >= self.threshold_context
                ]
                rejected_records.append(rec_rej)
            else:
                rejected_records.append(copy.copy(rec_acc))

        return accepted_records, rejected_records

    @staticmethod
    def _cosine_similarity(vec_a, vec_b):
        """Compute cosine similarity between two vectors."""
        norm_a = np.linalg.norm(vec_a)
        norm_b = np.linalg.norm(vec_b)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return float(np.dot(vec_a, vec_b) / (norm_a * norm_b))
