"""Pipeline to score context windows via semantic similarity against a reference NPS description."""

import copy
import logging

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
    2. The **document average** (mean of all window scores in a record) decides
       whether the file is accepted or rejected.
       * avg >= ``SIMILARITY_THRESHOLD_DOCUMENT_AVG``  →  accepted
       * avg <  threshold  →  rejected
    3. For **accepted** files the per-window threshold is applied: only windows
       with ``similarity_score >= SIMILARITY_THRESHOLD_CONTEXT_WINDOW`` are
       kept in the output written to ``json_processed/``.
    4. **Rejected** files are written to ``json_reject/`` with *all* windows
       (including scores) so the full picture is preserved for auditing.
    """

    def __init__(self):
        """Initialize embedding model and pre-compute the reference embedding."""
        logger.info("Loading embedding model '%s' …", Config.SIMILARITY_EMBEDDING_MODEL)
        self.embeddings = HuggingFaceEmbeddings(model_name=Config.SIMILARITY_EMBEDDING_MODEL)
        self.reference_embedding = np.array(
            self.embeddings.embed_query(Config.SIMILARITY_REFERENCE_TEXT)
        )
        self.threshold_context = Config.SIMILARITY_THRESHOLD_CONTEXT_WINDOW
        self.threshold_document = Config.SIMILARITY_THRESHOLD_DOCUMENT_AVG
        logger.info(
            "Similarity pipeline ready  (window threshold=%.2f, document threshold=%.2f)",
            self.threshold_context,
            self.threshold_document,
        )

    def similarity_workflow(self, records):
        """Score every context window and decide whether the file should be rejected.

        Args:
            records: list of dicts, each with optional ``context`` list produced
                     by the filtering step.

        Returns:
            tuple[list, list, bool]:
                - *scored_records*: deep copy with all windows and scores
                  (used for ``json_reject`` when the file is rejected).
                - *filtered_records*: records with only above-threshold windows
                  (used for ``json_processed`` when the file is accepted).
                - *should_reject*: ``True`` when the document average of any
                  record falls below ``SIMILARITY_THRESHOLD_DOCUMENT_AVG``.
        """
        should_reject = False

        for record in records:
            contexts = record.get("context", [])
            if not contexts:
                record["document_avg_similarity"] = None
                continue

            context_texts = [ctx["context"] for ctx in contexts]
            context_embeddings = self.embeddings.embed_documents(context_texts)

            scores = []
            for ctx, emb in zip(contexts, context_embeddings):
                score = self._cosine_similarity(np.array(emb), self.reference_embedding)
                ctx["similarity_score"] = round(float(score), 4)
                scores.append(score)

            avg_score = sum(scores) / len(scores)
            record["document_avg_similarity"] = round(float(avg_score), 4)

            if avg_score < self.threshold_document:
                should_reject = True

        scored_records = copy.deepcopy(records)

        for record in records:
            contexts = record.get("context", [])
            if contexts:
                record["context"] = [
                    ctx for ctx in contexts
                    if ctx.get("similarity_score", 0) >= self.threshold_context
                ]

        return scored_records, records, should_reject

    @staticmethod
    def _cosine_similarity(vec_a, vec_b):
        """Compute cosine similarity between two vectors."""
        norm_a = np.linalg.norm(vec_a)
        norm_b = np.linalg.norm(vec_b)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return float(np.dot(vec_a, vec_b) / (norm_a * norm_b))
