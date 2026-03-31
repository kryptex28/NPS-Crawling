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
        for record in records:
            contexts = record.get("context", [])
            if "metadata" not in record:
                record["metadata"] = {}

            record["metadata"]["experiment"] = Config.PREPROCESSING_VERSION
            record["metadata"]["Context Windows total"] = len(contexts)

            if not contexts:
                record["metadata"]["Context Windows Accept"] = 0
                record["metadata"]["Context Windows Reject"] = 0
                continue

            context_texts = [ctx["context"] for ctx in contexts]
            context_embeddings = self.embeddings.embed_documents(context_texts)

            accepted_count = 0
            rejected_count = 0
            scores = []
            for ctx, emb in zip(contexts, context_embeddings):
                score = self._cosine_similarity(np.array(emb), self.reference_embedding)
                ctx["similarity_score"] = round(float(score), 4)
                scores.append(score)
                if score >= self.threshold_context:
                    accepted_count += 1
                else:
                    rejected_count += 1

            record["metadata"]["Context Windows Accept"] = accepted_count
            record["metadata"]["Context Windows Reject"] = rejected_count

            if scores:
                record["filings_average"] = round(float(sum(scores) / len(scores)), 4)
            else:
                record["filings_average"] = 0.0

        accepted_records = copy.deepcopy(records)
        rejected_records = copy.deepcopy(records)

        for rec_acc, rec_rej in zip(accepted_records, rejected_records):
            ctxs_acc = rec_acc.get("context", [])
            if ctxs_acc:
                rec_acc["context"] = [
                    ctx for ctx in ctxs_acc
                    if ctx.get("similarity_score", 0) >= self.threshold_context
                ]

            ctxs_rej = rec_rej.get("context", [])
            if ctxs_rej:
                rec_rej["context"] = [
                    ctx for ctx in ctxs_rej
                    if ctx.get("similarity_score", 0) < self.threshold_context
                ]

        return accepted_records, rejected_records

    @staticmethod
    def _cosine_similarity(vec_a, vec_b):
        """Compute cosine similarity between two vectors."""
        norm_a = np.linalg.norm(vec_a)
        norm_b = np.linalg.norm(vec_b)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return float(np.dot(vec_a, vec_b) / (norm_a * norm_b))
