"""Parse the classification model configuration JSONs and visualize their results.

Every model that has been evaluated stores its result under
``src/nps_crawling/classification/configurations/<model>/<hash>.json``. Each file
holds a ``evaluation_results`` block with up to three classification tasks:

* ``NPS Category``      - 7-label multi-label classification (positive class ``"1"``)
* ``Has Numeric NPS``   - binary classification (positive class ``"1"``)
* ``NPS Value Category``- 6 numeric fields, classes ``correct_value`` / ``no_value`` / ``wrong_value``

Embedding models only carry the ``NPS Category`` task; LLM models carry all three.
Every task additionally stores a ``time_per_snippet`` (seconds) so we can reason about
the speed/quality trade-off.

The script turns those JSONs into a set of comparison graphics plus a tidy
``summary_metrics.csv`` written to ``configurations/graphics/``. Run it with the
project virtualenv::

    nps_venv/Scripts/python.exe train/visualize_model_evaluations.py
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # headless: only write files, never open a window
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# --------------------------------------------------------------------------- #
# Paths
# --------------------------------------------------------------------------- #
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
DEFAULT_CONFIG_DIR = REPO_ROOT / "src" / "nps_crawling" / "classification" / "configurations"

# --------------------------------------------------------------------------- #
# Task / label vocabulary (canonical order = order used in the category classes)
# --------------------------------------------------------------------------- #
TASK_NPS_CATEGORY = "NPS Category"
TASK_HAS_NUMERIC = "Has Numeric NPS"
TASK_VALUE_CATEGORY = "NPS Value Category"

NPS_CATEGORY_LABELS = [
    "KPI_CURRENT_VALUE",
    "KPI_TREND",
    "KPI_HISTORICAL_COMPARISON",
    "TARGET_OUTLOOK",
    "NPS_GOAL_REACHED",
    "METHODOLOGY_DEFINITION",
    "QUALITATIVE_ONLY",
]

NPS_VALUE_FIELDS = [
    "nps_value_fix",
    "nps_competition_industry",
    "nps_value_over",
    "nps_value_below",
    "nps_goal_value",
    "nps_goal_change",
]

# class_name -> coarse model family. Falls back to "available tasks" if unknown.
EMBEDDING_CLASSES = {"BGE_Base", "BGE_Advanced", "QWEN_Advanced"}


# --------------------------------------------------------------------------- #
# Loading / metric extraction
# --------------------------------------------------------------------------- #
def load_models(config_dir: Path) -> list[dict]:
    """Read every ``<model>/<hash>.json`` config and return parsed records.

    The ``graphics`` output directory is skipped. Each record keeps the model's
    display name (the parent folder), its python class, the family
    (Embedding/LLM) and the raw ``evaluation_results`` block.
    """
    records: list[dict] = []
    for json_path in sorted(config_dir.glob("*/*.json")):
        if json_path.parent.name == "graphics":
            continue
        with open(json_path, encoding="utf-8") as fh:
            data = json.load(fh)
        results = data.get("evaluation_results", {})
        if not results:
            print(f"  skip (no evaluation_results): {json_path}")
            continue
        class_name = data.get("class_name", "")
        # Family is a property of the model class, not of which tasks happened to
        # be evaluated (e.g. Mistral is an LLM even if only run on NPS Category).
        family = "Embedding" if class_name in EMBEDDING_CLASSES else "LLM"
        records.append(
            {
                "display_name": json_path.parent.name,
                "model_name": data.get("model_name", json_path.parent.name),
                "class_name": class_name,
                "family": family,
                "results": results,
            }
        )
    return records


def positive_f1(label_report: dict, positive_key: str = "1") -> float:
    """F1 of the positive class, or NaN if that class never occurs in the test set.

    sklearn omits the ``"1"`` key entirely when the positive support is 0 (e.g.
    bge-large on NPS_GOAL_REACHED) and emits an all-zero block with support 0 in
    other cases (e.g. gpt). Both are "not measurable", so we return NaN.
    """
    block = label_report.get(positive_key)
    if not isinstance(block, dict) or block.get("support", 0) == 0:
        return float("nan")
    return float(block.get("f1-score", float("nan")))


def metric(label_report: dict, key: str, field: str) -> float:
    """Generic getter for a (class, metric) pair, NaN-safe."""
    block = label_report.get(key)
    if not isinstance(block, dict) or block.get("support", 0) == 0:
        return float("nan")
    return float(block.get(field, float("nan")))


def macro_f1(label_report: dict) -> float:
    return float(label_report.get("macro avg", {}).get("f1-score", float("nan")))


def accuracy(label_report: dict) -> float:
    return float(label_report.get("accuracy", float("nan")))


# --------------------------------------------------------------------------- #
# DataFrame builders
# --------------------------------------------------------------------------- #
def build_nps_category_frames(records: list[dict]):
    """Return (positive_f1_df, macro_f1_df) indexed by model, columns = labels."""
    pos_rows, macro_rows, index = {}, {}, []
    for rec in records:
        task = rec["results"].get(TASK_NPS_CATEGORY)
        if not task:
            continue
        index.append(rec["display_name"])
        pos_rows[rec["display_name"]] = [
            positive_f1(task.get(lbl, {})) for lbl in NPS_CATEGORY_LABELS
        ]
        macro_rows[rec["display_name"]] = [
            macro_f1(task.get(lbl, {})) for lbl in NPS_CATEGORY_LABELS
        ]
    pos_df = pd.DataFrame.from_dict(pos_rows, orient="index", columns=NPS_CATEGORY_LABELS)
    macro_df = pd.DataFrame.from_dict(macro_rows, orient="index", columns=NPS_CATEGORY_LABELS)
    return pos_df, macro_df


def build_value_category_frame(records: list[dict]) -> pd.DataFrame:
    """correct_value F1 per value field, indexed by LLM model."""
    rows = {}
    for rec in records:
        task = rec["results"].get(TASK_VALUE_CATEGORY)
        if not task:
            continue
        rows[rec["display_name"]] = [
            metric(task.get(field, {}), "correct_value", "f1-score")
            for field in NPS_VALUE_FIELDS
        ]
    return pd.DataFrame.from_dict(rows, orient="index", columns=NPS_VALUE_FIELDS)


def build_timing_frame(records: list[dict]) -> pd.DataFrame:
    """time_per_snippet per (model, task) in seconds."""
    rows = {}
    for rec in records:
        rows[rec["display_name"]] = {
            task: rec["results"].get(task, {}).get("time_per_snippet", np.nan)
            for task in (TASK_NPS_CATEGORY, TASK_HAS_NUMERIC, TASK_VALUE_CATEGORY)
        }
    return pd.DataFrame.from_dict(rows, orient="index")


def build_has_numeric_frame(records: list[dict]) -> pd.DataFrame:
    """Accuracy + positive-class precision/recall/F1 for the binary task."""
    rows = {}
    for rec in records:
        task = rec["results"].get(TASK_HAS_NUMERIC)
        if not task:
            continue
        report = task.get("has_numeric_nps", {})
        rows[rec["display_name"]] = {
            "accuracy": accuracy(report),
            "precision (pos)": metric(report, "1", "precision"),
            "recall (pos)": metric(report, "1", "recall"),
            "f1 (pos)": metric(report, "1", "f1-score"),
        }
    return pd.DataFrame.from_dict(rows, orient="index")


# --------------------------------------------------------------------------- #
# Plot helpers
# --------------------------------------------------------------------------- #
def _annotated_heatmap(ax, frame: pd.DataFrame, cmap: str, vmin: float, vmax: float, fmt: str):
    """Draw an imshow heatmap with per-cell text; NaN cells rendered light grey."""
    data = np.ma.masked_invalid(frame.to_numpy(dtype=float))
    cmap_obj = plt.get_cmap(cmap).copy()
    cmap_obj.set_bad(color="0.85")
    im = ax.imshow(data, cmap=cmap_obj, vmin=vmin, vmax=vmax, aspect="auto")

    ax.set_xticks(range(frame.shape[1]))
    ax.set_xticklabels(frame.columns, rotation=40, ha="right", fontsize=9)
    ax.set_yticks(range(frame.shape[0]))
    ax.set_yticklabels(frame.index, fontsize=9)

    for r in range(frame.shape[0]):
        for c in range(frame.shape[1]):
            val = frame.iat[r, c]
            if np.isnan(val):
                ax.text(c, r, "n/a", ha="center", va="center", fontsize=7, color="0.4")
            else:
                # YlGn/PuBuGn go pale->dark, so only dark (high) cells need light text.
                shade = "white" if val >= vmin + 0.6 * (vmax - vmin) else "black"
                ax.text(c, r, format(val, fmt), ha="center", va="center", fontsize=8, color=shade)
    return im


def plot_nps_category_heatmap(pos_df: pd.DataFrame, out: Path):
    """Per-label positive-class F1 for every model (the cross-family common ground)."""
    df = pos_df.loc[pos_df.mean(axis=1, skipna=True).sort_values(ascending=False).index]
    fig, ax = plt.subplots(figsize=(11, 0.7 * len(df) + 2.5))
    im = _annotated_heatmap(ax, df, cmap="YlGn", vmin=0.0, vmax=1.0, fmt=".2f")
    fig.colorbar(im, ax=ax, fraction=0.025, pad=0.02, label="F1 (positive class)")
    ax.set_title(
        "NPS Category - positive-class F1 per label\n"
        "(all models; rows sorted by mean F1; 'n/a' = label absent from test set)",
        fontsize=12,
    )
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)


def plot_nps_category_ranking(pos_df: pd.DataFrame, macro_df: pd.DataFrame, out: Path):
    """Rank models on the common NPS Category task by mean F1 (positive + macro)."""
    summary = pd.DataFrame(
        {
            "mean positive-F1": pos_df.mean(axis=1, skipna=True),
            "mean macro-F1": macro_df.mean(axis=1, skipna=True),
        }
    ).sort_values("mean positive-F1", ascending=True)

    y = np.arange(len(summary))
    height = 0.38
    fig, ax = plt.subplots(figsize=(10, 0.8 * len(summary) + 2))
    b1 = ax.barh(y + height / 2, summary["mean positive-F1"], height, label="mean positive-class F1", color="#2b8cbe")
    b2 = ax.barh(y - height / 2, summary["mean macro-F1"], height, label="mean macro-avg F1", color="#a6bddb")
    ax.bar_label(b1, fmt="%.3f", padding=3, fontsize=8)
    ax.bar_label(b2, fmt="%.3f", padding=3, fontsize=8)
    ax.set_yticks(y)
    ax.set_yticklabels(summary.index)
    ax.set_xlim(0, 1.05)
    ax.set_xlabel("F1 (mean over 7 NPS Category labels)")
    ax.set_title("Model ranking on the NPS Category task")
    ax.legend(loc="lower right")
    ax.grid(axis="x", alpha=0.3)
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)


def plot_timing(timing_df: pd.DataFrame, out: Path):
    """Grouped bar of seconds/snippet per task per model (log scale)."""
    df = timing_df.sort_values(TASK_NPS_CATEGORY)
    tasks = [TASK_NPS_CATEGORY, TASK_HAS_NUMERIC, TASK_VALUE_CATEGORY]
    colors = {TASK_NPS_CATEGORY: "#1b9e77", TASK_HAS_NUMERIC: "#d95f02", TASK_VALUE_CATEGORY: "#7570b3"}

    x = np.arange(len(df))
    width = 0.26
    fig, ax = plt.subplots(figsize=(11, 6))
    for i, task in enumerate(tasks):
        vals = df[task].to_numpy(dtype=float)
        offset = (i - 1) * width
        bars = ax.bar(x + offset, np.nan_to_num(vals, nan=0.0), width, label=task, color=colors[task])
        for bar, v in zip(bars, vals):
            if not np.isnan(v) and v > 0:
                ax.text(bar.get_x() + bar.get_width() / 2, v, f"{v:.3g}",
                        ha="center", va="bottom", fontsize=7, rotation=90)
    ax.set_yscale("log")
    ax.set_xticks(x)
    ax.set_xticklabels(df.index, rotation=20, ha="right")
    ax.set_ylabel("seconds per snippet (log scale)")
    ax.set_title("Classification speed: time per snippet by task\n(lower is faster)")
    ax.legend(title="task")
    ax.grid(axis="y", which="both", alpha=0.3)
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)


def plot_quality_vs_speed(pos_df: pd.DataFrame, timing_df: pd.DataFrame, families: dict, out: Path):
    """Trade-off scatter: NPS Category quality vs speed, with the Pareto frontier."""
    quality = pos_df.mean(axis=1, skipna=True)
    speed = timing_df[TASK_NPS_CATEGORY]
    pts = pd.DataFrame({"quality": quality, "time": speed}).dropna()

    fam_color = {"Embedding": "#1f78b4", "LLM": "#e31a1c"}
    fig, ax = plt.subplots(figsize=(10, 7))
    for name, row in pts.iterrows():
        fam = families.get(name, "LLM")
        ax.scatter(row["time"], row["quality"], s=120, color=fam_color[fam],
                   edgecolor="black", zorder=3)
        ax.annotate(name, (row["time"], row["quality"]),
                    textcoords="offset points", xytext=(8, 4), fontsize=9)

    # Pareto frontier: want HIGH quality at LOW time. Sort by time ascending,
    # keep points whose quality exceeds everything seen so far (cheaper & better).
    frontier = pts.sort_values("time")
    best, keep = -np.inf, []
    for name, row in frontier.iterrows():
        if row["quality"] > best:
            keep.append((row["time"], row["quality"]))
            best = row["quality"]
    if len(keep) > 1:
        fx, fy = zip(*keep)
        ax.plot(fx, fy, "--", color="grey", zorder=2, label="Pareto frontier")
        ax.legend(loc="lower left")

    ax.set_xscale("log")
    ax.set_xlabel("time per snippet on NPS Category [s] (log scale, lower = faster)")
    ax.set_ylabel("mean positive-class F1 on NPS Category (higher = better)")
    ax.set_title("Quality vs. speed trade-off (NPS Category)\n"
                 "blue = embedding models, red = LLMs")
    ax.grid(True, which="both", alpha=0.3)
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)


def plot_has_numeric(frame: pd.DataFrame, out: Path):
    """Grouped bars of binary-task metrics for the LLM models that ran it."""
    df = frame.sort_values("f1 (pos)", ascending=False)
    metrics = list(df.columns)
    x = np.arange(len(df))
    width = 0.2
    colors = ["#4575b4", "#91bfdb", "#fc8d59", "#d73027"]
    fig, ax = plt.subplots(figsize=(10, 6))
    for i, m in enumerate(metrics):
        offset = (i - (len(metrics) - 1) / 2) * width
        bars = ax.bar(x + offset, df[m], width, label=m, color=colors[i % len(colors)])
        ax.bar_label(bars, fmt="%.2f", fontsize=7, padding=2)
    ax.set_xticks(x)
    ax.set_xticklabels(df.index, rotation=15, ha="right")
    ax.set_ylim(0, 1.05)
    ax.set_ylabel("score")
    ax.set_title("Has Numeric NPS - binary classification metrics (LLM models)")
    ax.legend(ncol=2)
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)


def plot_value_category_heatmap(frame: pd.DataFrame, out: Path):
    """correct_value F1 per value field, for the LLM models."""
    df = frame.loc[frame.mean(axis=1, skipna=True).sort_values(ascending=False).index]
    fig, ax = plt.subplots(figsize=(10, 0.7 * len(df) + 2.5))
    im = _annotated_heatmap(ax, df, cmap="PuBuGn", vmin=0.0, vmax=1.0, fmt=".2f")
    fig.colorbar(im, ax=ax, fraction=0.025, pad=0.02, label="F1 (correct_value)")
    ax.set_title(
        "NPS Value Category - value-extraction F1 per field (LLM models)\n"
        "F1 of the 'correct_value' class; 'n/a' = field absent from test set",
        fontsize=12,
    )
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)


# --------------------------------------------------------------------------- #
# Summary CSV
# --------------------------------------------------------------------------- #
def write_summary_csv(records, pos_df, macro_df, timing_df, has_numeric_df, value_df, out: Path):
    """One tidy row per model with the headline numbers behind the plots."""
    rows = []

    def cell(frame: pd.DataFrame, name: str, col: str, *, mean: bool = False):
        """NaN-safe lookup so models missing a whole task still get a row."""
        if name not in frame.index:
            return np.nan
        return frame.loc[name].mean(skipna=True) if mean else frame.loc[name, col]

    for rec in records:  # iterate the full set so no model is dropped
        name = rec["display_name"]
        rows.append(
            {
                "model": name,
                "model_name": rec["model_name"],
                "family": rec["family"],
                "nps_category_mean_positive_f1": cell(pos_df, name, None, mean=True),
                "nps_category_mean_macro_f1": cell(macro_df, name, None, mean=True),
                "nps_category_time_per_snippet_s": cell(timing_df, name, TASK_NPS_CATEGORY),
                "has_numeric_f1_pos": cell(has_numeric_df, name, "f1 (pos)"),
                "has_numeric_accuracy": cell(has_numeric_df, name, "accuracy"),
                "has_numeric_time_per_snippet_s": cell(timing_df, name, TASK_HAS_NUMERIC),
                "value_category_mean_correct_f1": cell(value_df, name, None, mean=True),
                "value_category_time_per_snippet_s": cell(timing_df, name, TASK_VALUE_CATEGORY),
            }
        )
    df = pd.DataFrame(rows).sort_values(
        "nps_category_mean_positive_f1", ascending=False, na_position="last"
    )
    df.to_csv(out, index=False, float_format="%.4f")
    return df


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--config-dir", type=Path, default=DEFAULT_CONFIG_DIR,
                        help="directory holding the <model>/<hash>.json config files")
    parser.add_argument("--out-dir", type=Path, default=None,
                        help="output directory for graphics (default: <config-dir>/graphics)")
    args = parser.parse_args()

    config_dir = args.config_dir.resolve()
    out_dir = (args.out_dir or config_dir / "graphics").resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"Reading model configs from: {config_dir}")
    records = load_models(config_dir)
    if not records:
        raise SystemExit("No evaluated model configs found.")
    print(f"Loaded {len(records)} model(s): " + ", ".join(f"{r['display_name']} [{r['family']}]" for r in records))

    pos_df, macro_df = build_nps_category_frames(records)
    timing_df = build_timing_frame(records)
    has_numeric_df = build_has_numeric_frame(records)
    value_df = build_value_category_frame(records)
    families = {r["display_name"]: r["family"] for r in records}

    print(f"Writing graphics to: {out_dir}")
    if not pos_df.empty:
        plot_nps_category_heatmap(pos_df, out_dir / "nps_category_positive_f1_heatmap.png")
        plot_nps_category_ranking(pos_df, macro_df, out_dir / "nps_category_model_ranking.png")
        plot_quality_vs_speed(pos_df, timing_df, families, out_dir / "quality_vs_speed_tradeoff.png")
    if not timing_df.empty:
        plot_timing(timing_df, out_dir / "speed_time_per_snippet.png")
    if not has_numeric_df.empty:
        plot_has_numeric(has_numeric_df, out_dir / "has_numeric_nps_comparison.png")
    if not value_df.empty:
        plot_value_category_heatmap(value_df, out_dir / "nps_value_category_correct_f1_heatmap.png")

    summary = write_summary_csv(records, pos_df, macro_df, timing_df, has_numeric_df, value_df,
                                out_dir / "summary_metrics.csv")

    print("\nSummary (sorted by NPS Category mean positive-F1):")
    with pd.option_context("display.max_columns", None, "display.width", 200):
        print(summary.to_string(index=False))
    print(f"\nDone. {len(list(out_dir.glob('*.png')))} figure(s) + summary_metrics.csv in {out_dir}")


if __name__ == "__main__":
    main()
