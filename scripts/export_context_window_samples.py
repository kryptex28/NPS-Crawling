"""Sample context windows per 0.1 similarity bucket and export to Excel.

For each experiment folder, reads context windows from both
``data/json_processed/`` and ``data/json_rejected/``, builds 0.1-wide buckets
covering the full similarity range, picks up to 2 context windows per bucket,
and writes one combined Excel file into ``scripts/context_windows_similarity/``.
"""

import json
import math
import random
from pathlib import Path

from openpyxl import Workbook

REPO_ROOT = Path(__file__).resolve().parent.parent
PROCESSED_DIR = REPO_ROOT / "data" / "json_processed"
REJECTED_DIR = REPO_ROOT / "data" / "json_rejected"
OUTPUT_DIR = Path(__file__).resolve().parent / "context_windows_similarity"

SAMPLES_PER_BUCKET = 5


def _load_summary(experiment_dir: Path) -> dict | None:
    """Return the preprocessing summary dict, or None if not found."""
    candidates = list(experiment_dir.glob("preprocessing_*.json"))
    if not candidates:
        return None
    with open(candidates[0], "r", encoding="utf-8") as f:
        return json.load(f)


def _collect_context_windows(data_dir: Path) -> list[dict]:
    """Return a flat list of {context, similarity_score} from all filing files."""
    files_dir = data_dir / "files"
    if not files_dir.is_dir():
        return []

    windows = []
    for json_file in sorted(files_dir.glob("*.json")):
        with open(json_file, "r", encoding="utf-8") as f:
            records = json.load(f)
        for record in records:
            for ctx in record.get("context", []):
                if "similarity_score" in ctx and "context" in ctx:
                    windows.append(
                        {
                            "context": ctx["context"],
                            "similarity_score": ctx["similarity_score"],
                            "matched_phrase": ctx.get("matched_phrase", ""),
                        }
                    )
    return windows


def _build_buckets(low: float, high: float) -> list[tuple[float, float]]:
    """Create 0.1-wide buckets covering [floor(low*10)/10 .. ceil(high*10)/10]."""
    start = math.floor(low * 10) / 10
    end = math.ceil(high * 10) / 10
    buckets = []
    current = round(start, 1)
    while current < end:
        buckets.append((round(current, 1), round(current + 0.1, 1)))
        current = round(current + 0.1, 1)
    return buckets


def _sample_windows(
    windows: list[dict],
    buckets: list[tuple[float, float]],
    n: int = SAMPLES_PER_BUCKET,
) -> list[dict]:
    """Pick up to *n* random windows per bucket."""
    samples = []
    for low, high in buckets:
        in_bucket = [
            w for w in windows if low <= w["similarity_score"] < high
        ]
        chosen = random.sample(in_bucket, min(n, len(in_bucket)))
        for w in chosen:
            samples.append(
                {
                    "context": w["context"],
                    "similarity_score": w["similarity_score"],
                    "matched_phrase": w["matched_phrase"],
                }
            )
    return samples


def _write_excel(
    experiment_name: str, rows: list[dict], output_dir: Path
) -> Path:
    """Write rows to an Excel file and return the path."""
    output_dir.mkdir(parents=True, exist_ok=True)
    wb = Workbook()
    ws = wb.active
    ws.title = "Context Window Samples"
    ws.append(["crawler_keyword", "context", "similarity_score", "matched_phrase"])
    for row in rows:
        ws.append([experiment_name, row["context"], row["similarity_score"], row["matched_phrase"]])
    path = output_dir / f"{experiment_name}.xlsx"
    wb.save(path)
    return path


def main():
    if not PROCESSED_DIR.is_dir():
        print(f"No processed directory found at {PROCESSED_DIR}")
        return

    for experiment_dir in sorted(PROCESSED_DIR.iterdir()):
        if not experiment_dir.is_dir():
            continue

        experiment_name = experiment_dir.name
        print(f"\nProcessing experiment: {experiment_name}")

        summary = _load_summary(experiment_dir)
        if not summary:
            print(f"  No preprocessing summary found — skipping")
            continue

        # Collect windows from both processed and rejected directories
        processed_windows = _collect_context_windows(experiment_dir)
        rejected_dir = REJECTED_DIR / experiment_name
        rejected_windows = _collect_context_windows(rejected_dir) if rejected_dir.is_dir() else []
        windows = processed_windows + rejected_windows
        print(f"  Found {len(processed_windows)} accepted + {len(rejected_windows)} rejected = {len(windows)} total context windows")

        if not windows:
            print("  No context windows found — skipping")
            continue

        # Derive similarity range from the actual data
        scores = [w["similarity_score"] for w in windows]
        low = min(scores)
        high = max(scores)
        print(f"  Similarity range: {low:.4f} – {high:.4f}")

        buckets = _build_buckets(low, high)
        print(f"  Buckets: {[f'{lo:.1f}-{hi:.1f}' for lo, hi in buckets]}")

        samples = _sample_windows(windows, buckets)
        print(f"  Sampled {len(samples)} context windows")

        if samples:
            path = _write_excel(experiment_name, samples, OUTPUT_DIR)
            print(f"  Written to {path}")


if __name__ == "__main__":
    main()
