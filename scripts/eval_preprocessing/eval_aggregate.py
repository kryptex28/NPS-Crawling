import csv
import re
import sys
from collections import defaultdict
from pathlib import Path

EVAL_DIR = Path(__file__).resolve().parents[2] / "evaluation" / "preprocessing"
RESULTS_DIR = EVAL_DIR / "results"

# Filename pattern: scores_<model_slug>__<ref_id>_metrics.csv
# The model slug itself can contain single underscores (e.g. "BAAI_bge-small-en-v1.5"),
# but the ``__`` (double underscore) before the ref_id is the unambiguous separator.
FILENAME_RE = re.compile(r"^scores_(?P<model>.+?)__(?P<ref>[^.]+)_metrics\.csv$")


def short_model_name(model_slug: str) -> str:
    """Strip vendor prefix and common 'sentence-transformers_' clutter."""
    name = model_slug
    for prefix in ("sentence-transformers_", "BAAI_"):
        if name.startswith(prefix):
            name = name[len(prefix):]
            break
    return name


def parse_metrics_csv(path: Path) -> dict | None:
    """Return the row with max F1 from one metrics CSV, plus timing."""
    best = None
    ms_per_ctx = None
    with open(path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                f1 = float(row["F1"])
            except (KeyError, TypeError, ValueError):
                continue
            if ms_per_ctx is None:
                raw = row.get("embedding_ms_per_context", "")
                if raw not in ("", None):
                    try:
                        ms_per_ctx = float(raw)
                    except ValueError:
                        pass
            if best is None or f1 > best["F1"]:
                best = {
                    "threshold": float(row["threshold"]),
                    "TP": int(row["TP"]),
                    "FP": int(row["FP"]),
                    "FN": int(row["FN"]),
                    "TN": int(row["TN"]),
                    "precision": float(row["precision"]),
                    "recall": float(row["recall"]),
                    "F1": f1,
                }
    if best is None:
        return None
    best["embedding_ms_per_context"] = ms_per_ctx
    return best


def collect() -> list[dict]:
    """Walk every metrics CSV in EVAL_DIR and return one record per file."""
    records = []
    for path in sorted(EVAL_DIR.glob("scores_*_metrics.csv")):
        m = FILENAME_RE.match(path.name)
        if not m:
            # Legacy files (e.g. scores_<model>_metrics.csv without a __ref) skipped.
            print(f"  skipping (no reference text in name): {path.name}", file=sys.stderr)
            continue
        best = parse_metrics_csv(path)
        if best is None:
            print(f"  skipping (no rows): {path.name}", file=sys.stderr)
            continue
        records.append({
            "model_slug": m.group("model"),
            "model": short_model_name(m.group("model")),
            "reference_text_id": m.group("ref"),
            **best,
            "source_file": path.name,
        })
    return records


def write_long_csv(records: list[dict], path: Path) -> None:
    cols = [
        "model", "reference_text_id", "F1", "threshold",
        "precision", "recall", "TP", "FP", "FN", "TN",
        "embedding_ms_per_context", "model_slug", "source_file",
    ]
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=cols)
        writer.writeheader()
        for r in records:
            writer.writerow({k: r.get(k, "") for k in cols})


def build_pivot(records: list[dict], value_fn) -> tuple[list[str], list[str], dict, dict]:
    """Pivot records into rows=model, cols=ref_id. Returns (row_labels, cols, cells, ms_per_model).

    ``value_fn(record)`` produces the cell value (string).
    """
    by_model: dict[str, dict[str, dict]] = defaultdict(dict)
    ms_per_model: dict[str, float | None] = {}
    for r in records:
        by_model[r["model"]][r["reference_text_id"]] = r
        # All ref texts share the same model timing — overwriting is fine.
        ms_per_model[r["model"]] = r.get("embedding_ms_per_context")

    # Preserve insertion order from the records list.
    models = list(by_model.keys())
    cols: list[str] = []
    seen = set()
    for r in records:
        rid = r["reference_text_id"]
        if rid not in seen:
            seen.add(rid)
            cols.append(rid)

    cells = {
        (model, ref): value_fn(by_model[model][ref])
        for model in models
        for ref in cols
        if ref in by_model[model]
    }
    return models, cols, cells, ms_per_model


def row_label(model: str, ms: float | None) -> str:
    if ms is None:
        return model
    return f"{model} ({ms:.1f} ms/ctx)"


def write_pivot_csv(records: list[dict], path: Path, value_fn) -> None:
    models, cols, cells, ms_per_model = build_pivot(records, value_fn)
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["model"] + cols)
        for m in models:
            writer.writerow(
                [row_label(m, ms_per_model[m])]
                + [cells.get((m, c), "") for c in cols]
            )


def print_markdown_table(records: list[dict], value_fn, title: str) -> None:
    models, cols, cells, ms_per_model = build_pivot(records, value_fn)
    if not models or not cols:
        print(f"\n{title}: no data")
        return
    headers = ["Model (embedding time)"] + cols
    rows = [
        [row_label(m, ms_per_model[m])] + [cells.get((m, c), "—") for c in cols]
        for m in models
    ]
    widths = [
        max(len(str(headers[i])), *(len(str(r[i])) for r in rows))
        for i in range(len(headers))
    ]
    def fmt_row(r):
        return "| " + " | ".join(str(r[i]).ljust(widths[i]) for i in range(len(r))) + " |"
    sep = "|" + "|".join("-" * (w + 2) for w in widths) + "|"
    print(f"\n### {title}\n")
    print(fmt_row(headers))
    print(sep)
    for r in rows:
        print(fmt_row(r))


def write_heatmap(records: list[dict], path: Path) -> None:
    """Render the F1 pivot as a heatmap with cell annotations."""
    try:
        import matplotlib
        matplotlib.use("Agg")  # headless backend; no Tk required
        import matplotlib.pyplot as plt
        import numpy as np
    except ImportError as exc:
        print(f"  Skipping heatmap ({exc}). Install matplotlib to enable.")
        return

    models, cols, cells, ms_per_model = build_pivot(
        records, value_fn=lambda r: r["F1"],
    )
    if not models or not cols:
        return

    matrix = np.array([
        [cells.get((m, c), np.nan) for c in cols]
        for m in models
    ], dtype=float)

    row_labels = [row_label(m, ms_per_model[m]) for m in models]

    fig_w = max(6.0, 1.4 * len(cols) + 4.0)
    fig_h = max(3.0, 0.7 * len(models) + 1.5)
    fig, ax = plt.subplots(figsize=(fig_w, fig_h))

    im = ax.imshow(matrix, aspect="auto", cmap="viridis", vmin=0.0, vmax=1.0)

    ax.set_xticks(range(len(cols)))
    ax.set_xticklabels(cols, rotation=30, ha="right")
    ax.set_yticks(range(len(models)))
    ax.set_yticklabels(row_labels)

    # Annotate each cell with its F1 value; pick text colour for contrast.
    for i in range(len(models)):
        for j in range(len(cols)):
            val = matrix[i, j]
            if np.isnan(val):
                ax.text(j, i, "—", ha="center", va="center", color="white", fontsize=9)
                continue
            colour = "white" if val < 0.55 else "black"
            ax.text(j, i, f"{val:.3f}", ha="center", va="center",
                    color=colour, fontsize=9)

    cbar = fig.colorbar(im, ax=ax, shrink=0.85)
    cbar.set_label("Best F1")

    ax.set_xlabel("Reference text")
    ax.set_title("Best F1 per (model, reference text)")
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def main():
    records = collect()
    if not records:
        print("No metrics CSVs found. Run eval_evaluate.py first.")
        return

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    long_path = RESULTS_DIR / "summary_long.csv"
    f1_path = RESULTS_DIR / "summary_best_f1.csv"
    f1_thr_path = RESULTS_DIR / "summary_best_f1_at_threshold.csv"
    heatmap_path = RESULTS_DIR / "heatmap_best_f1.png"

    write_long_csv(records, long_path)
    write_pivot_csv(records, f1_path, value_fn=lambda r: f"{r['F1']:.3f}")
    write_pivot_csv(
        records, f1_thr_path,
        value_fn=lambda r: f"{r['F1']:.3f} @ {r['threshold']:.2f}",
    )
    write_heatmap(records, heatmap_path)

    print(
        f"Wrote {long_path.name}, {f1_path.name}, {f1_thr_path.name}, "
        f"{heatmap_path.name} → {RESULTS_DIR}"
    )

    print_markdown_table(
        records,
        value_fn=lambda r: f"{r['F1']:.3f} @ {r['threshold']:.2f}",
        title="Best F1 per (model, reference text)  —  cell = F1 @ threshold",
    )
    print_markdown_table(
        records,
        value_fn=lambda r: f"{r['F1']:.3f}",
        title="Best F1 only (clean version)",
    )


if __name__ == "__main__":
    main()
