import json
import logging
import re
import sys
import time
from pathlib import Path

import numpy as np

# Allow running as a plain script without installing the package
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

# silence transformers noise the same way SimilarityPipeline does
import transformers
transformers.utils.logging.set_verbosity_error()
logging.getLogger("huggingface_hub").setLevel(logging.ERROR)

from langchain_huggingface import HuggingFaceEmbeddings

from eval_config import MODELS, REFERENCE_TEXTS


EVAL_DIR = Path(__file__).resolve().parents[2] / "evaluation" / "preprocessing"
CONTEXTS_JSONL = EVAL_DIR / "contexts.jsonl"


def model_slug(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", name).strip("_")


def detect_device() -> str:
    try:
        import torch
        if torch.cuda.is_available():
            return "cuda"
    except ImportError:
        pass
    return "cpu"


def cosine_scores(context_embeddings: np.ndarray, ref_embedding: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(context_embeddings, axis=1)
    ref_norm = np.linalg.norm(ref_embedding)
    dots = context_embeddings @ ref_embedding
    safe_divisor = norms * ref_norm
    safe_divisor[safe_divisor == 0] = 1.0
    return dots / safe_divisor


def load_contexts() -> list[dict]:
    rows = []
    with open(CONTEXTS_JSONL, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def score_with_model(model_name: str, rows: list[dict], device: str) -> None:
    texts = [row["context"] for row in rows]
    batch_size = 512 if device == "cuda" else 64

    print(f"\n=== {model_name} (device={device}) ===")
    print("Loading model …")
    embeddings = HuggingFaceEmbeddings(
        model_name=model_name,
        model_kwargs={"device": device},
        encode_kwargs={"batch_size": batch_size},
    )

    # Warm-up so model load + lazy init don't pollute the timed run.
    embeddings.embed_documents(texts[:1])

    t0 = time.perf_counter()
    context_embeddings = np.array(embeddings.embed_documents(texts))
    embedding_seconds_total = time.perf_counter() - t0
    embedding_ms_per_context = (embedding_seconds_total / len(rows)) * 1000.0

    print(
        f"Context embedding took {embedding_seconds_total:.3f}s "
        f"({embedding_ms_per_context:.2f} ms/context, "
        f"{len(rows) / embedding_seconds_total:.1f} contexts/sec) — "
        f"steady-state, excludes model load."
    )

    mslug = model_slug(model_name)
    for ref_id, ref_text in REFERENCE_TEXTS.items():
        ref_embedding = np.array(embeddings.embed_query(ref_text))
        scores = cosine_scores(context_embeddings, ref_embedding)

        out_path = EVAL_DIR / f"scores_{mslug}__{ref_id}.jsonl"
        with open(out_path, "w", encoding="utf-8") as f:
            for row, score in zip(rows, scores):
                f.write(json.dumps({
                    "context_id": row["context_id"],
                    "similarity_score": round(float(score), 6),
                    "model": model_name,
                    "device": device,
                    "reference_text_id": ref_id,
                    "reference_text": ref_text,
                    "embedding_seconds_total": round(embedding_seconds_total, 6),
                    "embedding_ms_per_context": round(embedding_ms_per_context, 6),
                }, ensure_ascii=False) + "\n")

        print(f"  [{ref_id}] wrote {len(rows)} scores to {out_path.name}")


def main():
    if not CONTEXTS_JSONL.exists():
        print(f"Missing {CONTEXTS_JSONL}. Run eval_export_for_labeling.py first.")
        return

    rows = load_contexts()
    if not rows:
        print("No context rows found.")
        return
    if not MODELS:
        print("No models defined in eval_config.MODELS.")
        return
    if not REFERENCE_TEXTS:
        print("No reference texts defined in eval_config.REFERENCE_TEXTS.")
        return

    device = detect_device()
    print(
        f"Eval grid: {len(MODELS)} model(s) × {len(REFERENCE_TEXTS)} reference text(s) "
        f"= {len(MODELS) * len(REFERENCE_TEXTS)} scores files. "
        f"{len(rows)} contexts. Device: {device}."
    )

    for model_name in MODELS:
        try:
            score_with_model(model_name, rows, device)
        except Exception as exc:
            print(f"  !! Skipping {model_name}: {exc}")


if __name__ == "__main__":
    main()
