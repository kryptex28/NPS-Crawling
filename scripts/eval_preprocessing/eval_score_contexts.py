"""Score the frozen evaluation context windows with the current similarity model.

Reads ``evaluation/preprocessing/contexts.jsonl`` (produced by
``eval_export_for_labeling.py``) and embeds every context window once with the
current ``SIMILARITY_EMBEDDING_MODEL``. The same embeddings are then scored
against every reference text defined in ``reference_texts.py``, producing one
JSONL per (model, reference text) pair:

    evaluation/preprocessing/scores_<model_slug>__<ref_id>.jsonl

To compare a different embedding model: edit ``SIMILARITY_EMBEDDING_MODEL`` in
``src/nps_crawling/config.py`` and rerun this script. To compare different
reference texts: edit ``reference_texts.py`` — no config change needed.

No threshold is applied here — raw cosine scores are stored so the threshold
sweep in ``eval_evaluate.py`` needs no re-embedding.
"""

import json
import re
import sys
import time
from pathlib import Path

import numpy as np

# Allow running as a plain script without installing the package
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from nps_crawling.config import Config
from nps_crawling.preprocessing.similarity import SimilarityPipeline

from reference_texts import REFERENCE_TEXTS


EVAL_DIR = Path(__file__).resolve().parents[2] / "evaluation" / "preprocessing"
CONTEXTS_JSONL = EVAL_DIR / "contexts.jsonl"


def model_slug(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", name).strip("_")


def cosine_scores(context_embeddings: np.ndarray, ref_embedding: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(context_embeddings, axis=1)
    ref_norm = np.linalg.norm(ref_embedding)
    dots = context_embeddings @ ref_embedding
    safe_divisor = norms * ref_norm
    safe_divisor[safe_divisor == 0] = 1.0
    return dots / safe_divisor


def main():
    if not CONTEXTS_JSONL.exists():
        print(f"Missing {CONTEXTS_JSONL}. Run eval_export_for_labeling.py first.")
        return

    rows = []
    with open(CONTEXTS_JSONL, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))

    if not rows:
        print("No context rows found.")
        return

    if not REFERENCE_TEXTS:
        print("No reference texts defined in reference_texts.py.")
        return

    print(
        f"Scoring {len(rows)} contexts with model '{Config.SIMILARITY_EMBEDDING_MODEL}' "
        f"against {len(REFERENCE_TEXTS)} reference text(s) …"
    )
    sim = SimilarityPipeline()
    texts = [row["context"] for row in rows]

    # Warm-up call so model load + lazy init don't pollute the timed run.
    sim.embeddings.embed_documents(texts[:1])

    # Time the context embedding once — independent of reference text.
    t0 = time.perf_counter()
    context_embeddings = np.array(sim.embeddings.embed_documents(texts))
    embedding_seconds_total = time.perf_counter() - t0
    embedding_ms_per_context = (embedding_seconds_total / len(rows)) * 1000.0

    print(
        f"Context embedding took {embedding_seconds_total:.3f}s "
        f"({embedding_ms_per_context:.2f} ms/context, "
        f"{len(rows) / embedding_seconds_total:.1f} contexts/sec) — "
        f"steady-state, excludes model load."
    )

    mslug = model_slug(Config.SIMILARITY_EMBEDDING_MODEL)
    for ref_id, ref_text in REFERENCE_TEXTS.items():
        ref_embedding = np.array(sim.embeddings.embed_query(ref_text))
        scores = cosine_scores(context_embeddings, ref_embedding)

        out_path = EVAL_DIR / f"scores_{mslug}__{ref_id}.jsonl"
        with open(out_path, "w", encoding="utf-8") as f:
            for row, score in zip(rows, scores):
                f.write(json.dumps({
                    "context_id": row["context_id"],
                    "similarity_score": round(float(score), 6),
                    "model": Config.SIMILARITY_EMBEDDING_MODEL,
                    "reference_text_id": ref_id,
                    "reference_text": ref_text,
                    "embedding_seconds_total": round(embedding_seconds_total, 6),
                    "embedding_ms_per_context": round(embedding_ms_per_context, 6),
                }, ensure_ascii=False) + "\n")

        print(f"  [{ref_id}] wrote {len(rows)} scores to {out_path.name}")


if __name__ == "__main__":
    main()
