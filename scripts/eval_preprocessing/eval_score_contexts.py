"""Score the frozen evaluation context windows with the current similarity model.

Reads ``evaluation/preprocessing/contexts.jsonl`` (produced by
``eval_export_for_labeling.py``) and runs ``SimilarityPipeline.embed_and_score``
on every row. Writes one JSONL of raw scores per run, named after the embedding
model so results from different model configs don't overwrite each other:

    evaluation/preprocessing/scores_<sanitized_model_name>.jsonl

To compare a different embedding model or a different ``SIMILARITY_REFERENCE_TEXT``,
edit ``src/nps_crawling/config.py`` and re-run this script. No threshold is
applied here — raw cosine scores are stored so threshold sweeps in
``eval_evaluate.py`` need no re-embedding.
"""

import json
import re
import sys
import time
from pathlib import Path

# Allow running as a plain script without installing the package
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from nps_crawling.config import Config
from nps_crawling.preprocessing.similarity import SimilarityPipeline


EVAL_DIR = Path(__file__).resolve().parents[2] / "evaluation" / "preprocessing"
CONTEXTS_JSONL = EVAL_DIR / "contexts.jsonl"


def model_slug(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", name).strip("_")


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

    print(f"Scoring {len(rows)} contexts with model '{Config.SIMILARITY_EMBEDDING_MODEL}' …")
    sim = SimilarityPipeline()
    texts = [row["context"] for row in rows]

    # Warm-up call so model load + lazy init don't pollute the timed run.
    sim.embed_and_score(texts[:1])

    t0 = time.perf_counter()
    scores = sim.embed_and_score(texts)
    embedding_seconds_total = time.perf_counter() - t0
    embedding_ms_per_context = (embedding_seconds_total / len(rows)) * 1000.0

    print(
        f"Embedding+scoring took {embedding_seconds_total:.3f}s "
        f"({embedding_ms_per_context:.2f} ms/context, "
        f"{len(rows) / embedding_seconds_total:.1f} contexts/sec) — "
        f"steady-state, excludes model load."
    )

    out_path = EVAL_DIR / f"scores_{model_slug(Config.SIMILARITY_EMBEDDING_MODEL)}.jsonl"
    with open(out_path, "w", encoding="utf-8") as f:
        for row, score in zip(rows, scores):
            f.write(json.dumps({
                "context_id": row["context_id"],
                "similarity_score": round(float(score), 6),
                "model": Config.SIMILARITY_EMBEDDING_MODEL,
                "reference_text": Config.SIMILARITY_REFERENCE_TEXT,
                "embedding_seconds_total": round(embedding_seconds_total, 6),
                "embedding_ms_per_context": round(embedding_ms_per_context, 6),
            }, ensure_ascii=False) + "\n")

    print(f"Wrote {len(rows)} scores to {out_path}")


if __name__ == "__main__":
    main()
