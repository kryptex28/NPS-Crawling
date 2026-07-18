"""Curated, paper-ready evaluation figures for the NPS classification study.

Unlike ``visualize_model_evaluations.py`` (which plots *every* evaluated config
and has grown unreadable), this script hand-picks one representative per core
approach plus the configs needed for the within-approach comparisons, and adds
a dataset-composition analysis (class imbalance / label support).

Approaches covered:

* **Embedding + SVM** - Qwen3-Embedding-4B (the production backbone) and the
  backbone sweep that led to it. Production uses the unified ``SVM`` class
  (``svm.py``), which routes boolean properties through the shared-instruction
  path (its SVMs are interchangeable with ``QWEN_Advanced(optimized=true)``,
  config 6206df79) and numeric properties through the ``QWEN_Candidate`` path
  (config 97f7992a); those two evals therefore stand in for production.
* **Local LLM**       - Qwen3-8B (best local LLM), Mistral-7B as contrast.
* **API LLM**         - gpt-5.4 (few-shot) and gpt-5.4-mini.

Value-extraction ("NPS Value Category") figures only include runs made after
the NaN-handling eval fix (2026-07-02); older runs are inflated and skipped.

Figures + ``paper_summary.csv`` go to ``configurations/graphics/paper/``; every
figure is written as 300-dpi PNG and as PDF (for LaTeX). Run with::

    KMP_DUPLICATE_LIB_OK=TRUE python train/visualize_paper_evaluation.py
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.transforms as mtransforms
import numpy as np
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from visualize_model_evaluations import (  # noqa: E402
    DEFAULT_CONFIG_DIR,
    NPS_CATEGORY_LABELS,
    NPS_VALUE_FIELDS,
    TASK_HAS_NUMERIC,
    TASK_NPS_CATEGORY,
    TASK_VALUE_CATEGORY,
    accuracy,
    load_models,
    macro_f1,
    metric,
    positive_f1,
)

# The whole eval corpus was computed against the "without examples" ground
# truth (697 rows, test n = 349): the 6 hand-selected few-shot example snippets
# are excluded so they can never leak into the hold-out set. Dataset statistics
# use the same file so figure supports are consistent with the eval JSONs.
GROUND_TRUTH_CSV = SCRIPT_DIR / "ground_truth_final_without_examples.csv"

# --------------------------------------------------------------------------- #
# Style: validated light-mode palette (see dataviz reference palette)
# --------------------------------------------------------------------------- #
INK = "#0b0b0b"        # primary text
INK2 = "#52514e"       # secondary text / annotations
MUTED = "#898781"      # axis tick labels
GRID = "#e1e0d9"       # hairline grid
AXIS = "#c3c2b7"       # axis spines

# Categorical slots in fixed, CVD-safe order.
C1_BLUE = "#2a78d6"
C2_AQUA = "#1baf7a"
C3_YELLOW = "#eda100"
C4_GREEN = "#008300"
C5_VIOLET = "#4a3aa7"
C6_RED = "#e34948"

# Single-hue sequential ramp (blue 100 -> 700) for heatmaps.
SEQ_BLUE = LinearSegmentedColormap.from_list(
    "seq_blue",
    ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"],
)

APPROACH_COLOR = {
    "Embedding + SVM": C1_BLUE,
    "Local LLM": C2_AQUA,
    "API LLM": C3_YELLOW,
}
APPROACH_MARKER = {"Embedding + SVM": "o", "Local LLM": "^", "API LLM": "s"}


def _style() -> None:
    plt.rcParams.update(
        {
            "font.size": 9,
            "font.family": "sans-serif",
            "text.color": INK,
            "axes.edgecolor": AXIS,
            "axes.labelcolor": INK2,
            "axes.titlecolor": INK,
            "axes.linewidth": 0.8,
            "xtick.color": MUTED,
            "ytick.color": MUTED,
            "xtick.labelcolor": INK2,
            "ytick.labelcolor": INK2,
            "grid.color": GRID,
            "grid.linewidth": 0.8,
            "legend.frameon": False,
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "savefig.facecolor": "white",
        }
    )


def _despine(ax, keep=("left", "bottom")) -> None:
    for side in ("top", "right", "left", "bottom"):
        ax.spines[side].set_visible(side in keep)


def _save(fig, out_dir: Path, stem: str) -> None:
    fig.savefig(out_dir / f"{stem}.png", dpi=300, bbox_inches="tight")
    fig.savefig(out_dir / f"{stem}.pdf", bbox_inches="tight")
    plt.close(fig)
    print(f"  wrote {stem}.png / .pdf")


# --------------------------------------------------------------------------- #
# Curated config selection (folder, hash-prefix) -> paper identity
# --------------------------------------------------------------------------- #
# roles: "headline" = cross-approach representative, "embedding"/"llm" =
# within-approach comparison, "value" = numeric value extraction, "scatter" =
# quality-vs-speed plot.
CURATED: dict[str, dict] = {
    # ---- Embedding + SVM (production approach) ----
    "ceedaa3a": {
        "label": "Qwen3-Emb-4B + SVM (production)",
        "short": "Qwen3-Emb-4B (prod.)",
        "approach": "Embedding + SVM",
        "roles": {"headline", "embedding", "value", "scatter"},
    },
    "4df73844": {
        "label": "bge-m3 + BGE_SVM (native, unified)",
        "short": "bge-m3 (native)",
        "approach": "Embedding + SVM",
        "roles": {"headline", "embedding", "value", "scatter"},
    },
    "c7d19631": {
        "label": "Qwen3-Emb-4B + SVM (per-property instr.)",
        "short": "Qwen3-Emb-4B (per-prop.)",
        "approach": "Embedding + SVM",
        "roles": {"headline", "embedding", "scatter"},
    },
    "7a55b4c0": {
        "label": "bge-m3 + SVM (Qwen-style pipeline)",
        "short": "bge-m3 (Qwen-style)",
        "approach": "Embedding + SVM",
        "roles": {"embedding"},
    },
    "8f280220": {
        "label": "Qwen3-Emb-0.6B + SVM (shared instr.)",
        "short": "Qwen3-Emb-0.6B",
        "approach": "Embedding + SVM",
        "roles": {"embedding", "scatter"},
    },
    "d8fc9e67": {
        "label": "bge-m3 + SVM (per-property instr.)",
        "short": "bge-m3 (per-prop.)",
        "approach": "Embedding + SVM",
        "roles": {"embedding"},
    },
    "1c5568c0": {
        "label": "bge-large-en-v1.5 + SVM (per-property instr.)",
        "short": "bge-large-en-v1.5",
        "approach": "Embedding + SVM",
        "roles": {"embedding"},
    },
    "c7d25c71": {
        "label": "all-MiniLM-L6-v2 + SVM (hand-sel. examples)",
        "short": "all-MiniLM-L6-v2",
        "approach": "Embedding + SVM",
        "roles": {"embedding", "scatter"},
    },
    "600438fa": {
        "label": "par.-mult.-MiniLM-L12-v2 + SVM (hand-sel. examples)",
        "short": "para-MiniLM-L12-v2",
        "approach": "Embedding + SVM",
        "roles": {"embedding"},
    },
    "71e39d0c": {
        "label": "par.-mult.-mpnet-base-v2 + SVM (hand-sel. examples)",
        "short": "para-mpnet-base-v2",
        "approach": "Embedding + SVM",
        "roles": {"embedding"},
    },
    # ---- Local LLMs ----
    "fc71e466": {
        "label": "Qwen3-8B (thinking)",
        "short": "Qwen3-8B (think)",
        "approach": "Local LLM",
        "roles": {"headline", "llm", "scatter"},
    },
    "6bc7884b": {
        "label": "Qwen3-8B (no thinking)",
        "short": "Qwen3-8B",
        "approach": "Local LLM",
        "roles": {"headline", "llm", "value", "scatter"},
    },
    "e941f85a": {
        "label": "Mistral-7B-Instruct-v0.2",
        "short": "Mistral-7B",
        "approach": "Local LLM",
        "roles": {"llm", "scatter"},
    },
    # ---- API LLMs ----
    "c0e8d13d": {
        "label": "gpt-5.4 (hand-sel. examples)",
        "short": "gpt-5.4 (few-shot)",
        "approach": "API LLM",
        "roles": {"headline", "llm", "scatter"},
    },
    "c8c1da99": {
        "label": "gpt-5.4-mini",
        "short": "gpt-5.4-mini",
        "approach": "API LLM",
        "roles": {"headline", "llm", "value", "scatter"},
    },
    # ---- Numeric value extraction (candidate SVMs) ----
    "40f7d149": {
        "label": "Qwen3-Emb-0.6B + SVM (candidate)",
        "short": "Qwen3-Emb-0.6B (cand.)",
        "approach": "Embedding + SVM",
        "roles": {"value"},
    },
}

# Order used everywhere a "headline" comparison appears (canonical-split only).
HEADLINE_ORDER = ["c7d19631", "ceedaa3a", "4df73844", "6bc7884b", "c0e8d13d", "c8c1da99"]

# The two-model production comparison (fig 8).
PROD_PAIR = ["ceedaa3a", "4df73844"]

# Canonical test split (ground_truth_final_without_examples.csv, seed 42,
# test n = 349), identified by two invariant positive supports. Several older
# evals were run against earlier dataset versions and are flagged with ``‡``.
CANONICAL_CAT_SUPPORT = 159.0    # KPI_CURRENT_VALUE positives
CANONICAL_VALUE_SUPPORT = 146.0  # nps_value_fix rows with a value
SPLIT_MARK = " ‡"           # ‡


def _pos_support(report: dict) -> float | None:
    pos = report.get("True") or report.get("1") or {}
    return pos.get("support")


def _flag_splits(rec: dict) -> None:
    """Attach cat/value split-consistency flags (None = task absent)."""
    cat = rec["results"].get(TASK_NPS_CATEGORY)
    rec["cat_canonical"] = (
        _pos_support(cat.get("KPI_CURRENT_VALUE", {})) == CANONICAL_CAT_SUPPORT
        if cat else None
    )
    val = rec["results"].get(TASK_VALUE_CATEGORY)
    cv = (val.get("nps_value_fix") or {}).get("correct_value") if val else None
    rec["value_canonical"] = (
        (cv or {}).get("support") == CANONICAL_VALUE_SUPPORT if val else None
    )


def marked_label(prefix: str, rec: dict, flag_key: str) -> str:
    label = CURATED[prefix]["label"]
    return label + SPLIT_MARK if rec.get(flag_key) is False else label


def select_curated(records: list[dict]) -> dict[str, dict]:
    """Map hash-prefix -> record for every curated config; warn about misses."""
    by_prefix = {}
    for rec in records:
        for prefix in CURATED:
            if rec["hash"].startswith(prefix):
                _flag_splits(rec)
                by_prefix[prefix] = rec
    missing = set(CURATED) - set(by_prefix)
    if missing:
        print(f"  WARNING: curated configs not found: {sorted(missing)}")
    return by_prefix


def by_role(selected: dict[str, dict], role: str) -> list[str]:
    return [p for p in CURATED if role in CURATED[p]["roles"] and p in selected]


# --------------------------------------------------------------------------- #
# Support extraction
# --------------------------------------------------------------------------- #
def test_supports(selected: dict[str, dict]) -> dict[str, float]:
    """Positive-class support per boolean label in the (shared) test split."""
    supports: dict[str, float] = {}
    rec = selected.get("ceedaa3a") or next(iter(selected.values()))
    task = rec["results"].get(TASK_NPS_CATEGORY, {})
    for lbl in NPS_CATEGORY_LABELS:
        block = task.get(lbl, {}).get("True") or task.get(lbl, {}).get("1") or {}
        supports[lbl] = block.get("support", np.nan)
    hn = rec["results"].get(TASK_HAS_NUMERIC, {}).get("has_numeric_nps", {})
    block = hn.get("True") or hn.get("1") or {}
    supports["has_numeric_nps"] = block.get("support", np.nan)
    supports["_n_test"] = task.get(NPS_CATEGORY_LABELS[0], {}).get("macro avg", {}).get("support", np.nan)
    return supports


def value_test_supports(selected: dict[str, dict]) -> dict[str, float]:
    """correct_value support per numeric field (rows whose ground truth has a value)."""
    rec = selected.get("c8c1da99") or selected.get("ceedaa3a")
    task = rec["results"].get(TASK_VALUE_CATEGORY, {}) if rec else {}
    return {
        f: (task.get(f, {}).get("correct_value") or {}).get("support", np.nan)
        for f in NPS_VALUE_FIELDS
    }


# --------------------------------------------------------------------------- #
# Figure 1 - dataset composition / class imbalance
# --------------------------------------------------------------------------- #
def fig_dataset_composition(out_dir: Path) -> pd.DataFrame:
    from sklearn.model_selection import train_test_split

    df = pd.read_csv(GROUND_TRUTH_CSV)
    n = len(df)
    # Same seeded 50/50 split every evaluation uses
    # (ground_truth_train_test_split: seed 42, test_size 0.5).
    train_df, test_df = train_test_split(df, test_size=0.5, random_state=42)
    if float(test_df["KPI_CURRENT_VALUE"].sum()) != CANONICAL_CAT_SUPPORT:
        print("  WARNING: reproduced split does not match the canonical eval split")

    bool_labels = NPS_CATEGORY_LABELS + ["has_numeric_nps"]
    bool_counts = df[bool_labels].sum().astype(int)
    value_counts = df[NPS_VALUE_FIELDS].notna().sum().astype(int)

    fig, (ax1, ax2) = plt.subplots(
        1, 2, figsize=(8.6, 3.4), gridspec_kw={"width_ratios": [4, 3]}
    )

    panels = (
        (ax1, bool_labels, lambda d, c: int(d[c].sum()), "Boolean properties (positive class)"),
        (ax2, NPS_VALUE_FIELDS, lambda d, c: int(d[c].notna().sum()), "Numeric fields (value present)"),
    )
    for ax, cols, count, title in panels:
        totals = pd.Series({c: count(df, c) for c in cols}).sort_values()
        tr = np.array([count(train_df, c) for c in totals.index])
        te = np.array([count(test_df, c) for c in totals.index])
        y = np.arange(len(totals))
        ax.barh(y, tr, height=0.62, color=C1_BLUE, edgecolor="white", linewidth=0.8,
                label=f"train fold (n = {len(train_df)})")
        ax.barh(y, te, left=tr, height=0.62, color=C2_AQUA, edgecolor="white", linewidth=0.8,
                label=f"test fold (n = {len(test_df)})")
        ax.set_yticks(y)
        ax.set_yticklabels(totals.index, fontsize=8)
        for yi, total, a, b in zip(y, totals.values, tr, te):
            ax.text(total + n * 0.012, yi, f"{total} ({total / n:.0%}) · {a}/{b}",
                    va="center", fontsize=7, color=INK2)
        ax.set_xlim(0, n)
        ax.axvline(n, color=AXIS, lw=0.8, ls=(0, (3, 3)))
        ax.set_title(title, fontsize=9.5, loc="left")
        ax.grid(axis="x", lw=0.8, color=GRID)
        ax.set_axisbelow(True)
        _despine(ax)

    ax1.legend(loc="lower right", fontsize=7.5)
    fig.suptitle(
        f"Ground-truth dataset composition ({n} annotated snippets; "
        "annotations: total (share) · train/test)",
        fontsize=11, x=0.02, ha="left",
    )
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    _save(fig, out_dir, "fig1_dataset_composition")

    return pd.DataFrame({"positives": bool_counts, "share": bool_counts / n})


# --------------------------------------------------------------------------- #
# Figure 2 - cross-approach per-label F1 heatmap
# --------------------------------------------------------------------------- #
def _annotated_heatmap(ax, frame: pd.DataFrame, vmax: float = 1.0):
    data = np.ma.masked_invalid(frame.to_numpy(dtype=float))
    cmap = SEQ_BLUE.copy()
    cmap.set_bad(color="#f0efec")
    im = ax.imshow(data, cmap=cmap, vmin=0.0, vmax=vmax, aspect="auto")
    for r in range(frame.shape[0]):
        for c in range(frame.shape[1]):
            val = frame.iat[r, c]
            if np.isnan(val):
                ax.text(c, r, "n/a", ha="center", va="center", fontsize=7, color=MUTED)
            else:
                shade = "white" if val >= 0.6 * vmax else INK
                ax.text(c, r, f"{val:.2f}", ha="center", va="center", fontsize=8, color=shade)
    ax.set_xticks(range(frame.shape[1]))
    ax.set_yticks(range(frame.shape[0]))
    ax.tick_params(length=0)
    for side in ("top", "right", "left", "bottom"):
        ax.spines[side].set_visible(False)
    return im


def fig_headline_per_label(selected, supports, out_dir: Path) -> pd.DataFrame:
    labels = sorted(NPS_CATEGORY_LABELS, key=lambda l: -supports[l])
    cols = labels + ["has_numeric_nps"]
    rows = {}
    for prefix in HEADLINE_ORDER:
        rec = selected[prefix]
        cat = rec["results"].get(TASK_NPS_CATEGORY, {})
        vals = [positive_f1(cat.get(l, {})) for l in labels]
        hn = rec["results"].get(TASK_HAS_NUMERIC, {}).get("has_numeric_nps")
        vals.append(positive_f1(hn) if hn else np.nan)
        rows[CURATED[prefix]["label"]] = vals
    frame = pd.DataFrame.from_dict(rows, orient="index", columns=cols)
    frame["mean (7 labels)"] = frame[labels].mean(axis=1, skipna=True)

    fig, ax = plt.subplots(figsize=(8.2, 0.55 * len(frame) + 2.2))
    im = _annotated_heatmap(ax, frame)
    ax.set_xticklabels(
        [f"{c}\n(n = {supports[c]:.0f})" if c in supports else c for c in frame.columns],
        rotation=35, ha="right", fontsize=7.5,
    )
    ax.set_yticklabels(frame.index, fontsize=8.5)
    fig.colorbar(im, ax=ax, fraction=0.03, pad=0.02).set_label("positive-class F1", fontsize=8)
    ax.set_title(
        "Per-label positive-class F1 by approach\n"
        "columns sorted by positive support in the test split (n = 349)",
        fontsize=10.5, loc="left",
    )
    fig.tight_layout()
    _save(fig, out_dir, "fig2_approaches_per_label_f1")
    return frame


# --------------------------------------------------------------------------- #
# Figure 3 - label support vs positive F1 (imbalance effect)
# --------------------------------------------------------------------------- #
SHORT_LABEL = {
    "KPI_CURRENT_VALUE": "KPI CURRENT VALUE",
    "KPI_TREND": "KPI TREND",
    "KPI_HISTORICAL_COMPARISON": "KPI HIST. COMPARISON",
    "TARGET_OUTLOOK": "TARGET OUTLOOK",
    "NPS_GOAL_REACHED": "NPS GOAL REACHED",
    "METHODOLOGY_DEFINITION": "METHODOLOGY DEF.",
    "QUALITATIVE_ONLY": "QUALITATIVE ONLY",
}


def fig_support_vs_f1(selected, supports, out_dir: Path) -> None:
    fig, ax = plt.subplots(figsize=(6.8, 4.4))
    slot_colors = [C1_BLUE, C2_AQUA, C3_YELLOW, C4_GREEN, C5_VIOLET]
    markers = ["o", "s", "^", "D", "v"]

    for (prefix, color, marker) in zip(HEADLINE_ORDER, slot_colors, markers):
        rec = selected[prefix]
        cat = rec["results"].get(TASK_NPS_CATEGORY, {})
        xs, ys = [], []
        for lbl in NPS_CATEGORY_LABELS:
            f1 = positive_f1(cat.get(lbl, {}))
            if not np.isnan(f1):
                xs.append(supports[lbl])
                ys.append(f1)
        ax.scatter(xs, ys, s=52, color=color, marker=marker, zorder=3,
                   edgecolor="white", linewidth=0.8,
                   label=CURATED[prefix]["short"])

    blend = mtransforms.blended_transform_factory(ax.transData, ax.transAxes)
    for lbl in NPS_CATEGORY_LABELS:
        ax.text(supports[lbl], 1.02, SHORT_LABEL[lbl], rotation=90, transform=blend,
                ha="center", va="bottom", fontsize=6.5, color=MUTED)
        ax.axvline(supports[lbl], color=GRID, lw=0.8, zorder=1)

    ax.set_xscale("log")
    ax.set_xlabel("positive support in test split (log scale)")
    ax.set_ylabel("positive-class F1")
    ax.set_ylim(-0.04, 1.04)
    ax.grid(axis="y", lw=0.8, color=GRID)
    ax.set_axisbelow(True)
    _despine(ax)
    # The gap between NPS_GOAL_REACHED (n=2) and TARGET_OUTLOOK (n=17) is empty.
    ax.legend(loc="center left", bbox_to_anchor=(0.08, 0.5), fontsize=7.5)
    ax.set_title("Label support vs. classification quality",
                 fontsize=10.5, loc="left", pad=78)
    fig.tight_layout()
    _save(fig, out_dir, "fig3_support_vs_f1")


# --------------------------------------------------------------------------- #
# Figure 4 - embedding backbone comparison (within-approach)
# --------------------------------------------------------------------------- #
def fig_embedding_backbones(selected, out_dir: Path) -> None:
    rows = {}
    for prefix in by_role(selected, "embedding"):
        rec = selected[prefix]
        cat = rec["results"].get(TASK_NPS_CATEGORY, {})
        rows[marked_label(prefix, rec, "cat_canonical")] = {
            "mean positive-class F1": np.nanmean([positive_f1(cat.get(l, {})) for l in NPS_CATEGORY_LABELS]),
            "mean macro-avg F1": np.nanmean([macro_f1(cat.get(l, {})) for l in NPS_CATEGORY_LABELS]),
            "_prod": prefix == "ceedaa3a",
        }
    df = pd.DataFrame.from_dict(rows, orient="index").sort_values("mean positive-class F1")
    has_marked = any(SPLIT_MARK in name for name in df.index)

    y = np.arange(len(df))
    h = 0.36
    fig, ax = plt.subplots(figsize=(7.2, 0.42 * len(df) + 1.8))
    b1 = ax.barh(y + h / 2, df["mean positive-class F1"], h, color=C1_BLUE,
                 label="mean positive-class F1")
    b2 = ax.barh(y - h / 2, df["mean macro-avg F1"], h, color=C2_AQUA,
                 label="mean macro-avg F1")
    ax.bar_label(b1, fmt="%.3f", padding=3, fontsize=7, color=INK2)
    ax.bar_label(b2, fmt="%.3f", padding=3, fontsize=7, color=INK2)
    ax.set_yticks(y)
    labels = []
    for name, row in df.iterrows():
        labels.append(name + ("  ★" if row["_prod"] else ""))
    ax.set_yticklabels(labels, fontsize=8.5)
    ax.set_xlim(0, 1.0)
    ax.set_xlabel("F1 (mean over the 7 NPS Category labels)")
    ax.grid(axis="x", lw=0.8, color=GRID)
    ax.set_axisbelow(True)
    _despine(ax)
    ax.legend(loc="lower left", bbox_to_anchor=(0, 1.0), ncol=2, fontsize=8)
    title = ("Embedding backbones for the SVM approach (NPS Category)\n"
             "★ = boolean path of the production model (unified SVM class)")
    if has_marked:
        title += "\n‡ = evaluated on an outdated test split; not directly comparable"
    ax.set_title(title, fontsize=10.5, loc="left", pad=26)
    fig.tight_layout()
    _save(fig, out_dir, "fig4_embedding_backbones")


# --------------------------------------------------------------------------- #
# Figure 5 - LLM comparison (local vs API, within-approach)
# --------------------------------------------------------------------------- #
def fig_llm_comparison(selected, out_dir: Path) -> None:
    rows = {}
    for prefix in by_role(selected, "llm"):
        rec = selected[prefix]
        cat = rec["results"].get(TASK_NPS_CATEGORY, {})
        hn = rec["results"].get(TASK_HAS_NUMERIC, {}).get("has_numeric_nps")
        rows[marked_label(prefix, rec, "cat_canonical")] = {
            "NPS Category (mean pos. F1)": np.nanmean([positive_f1(cat.get(l, {})) for l in NPS_CATEGORY_LABELS]),
            "Has Numeric NPS (pos. F1)": positive_f1(hn) if hn else np.nan,
            "_approach": CURATED[prefix]["approach"],
        }
    df = pd.DataFrame.from_dict(rows, orient="index")
    # Local block first, API block second; best-first inside each block.
    df["_grp"] = (df["_approach"] == "API LLM").astype(int)
    df = df.sort_values(["_grp", "NPS Category (mean pos. F1)"], ascending=[False, True])

    y = np.arange(len(df))
    h = 0.36
    fig, ax = plt.subplots(figsize=(7.2, 0.5 * len(df) + 1.9))
    b1 = ax.barh(y + h / 2, df["NPS Category (mean pos. F1)"], h, color=C1_BLUE,
                 label="NPS Category (mean positive-class F1)")
    hn_vals = df["Has Numeric NPS (pos. F1)"].to_numpy(float)
    b2 = ax.barh(y - h / 2, np.nan_to_num(hn_vals), h, color=C2_AQUA,
                 label="Has Numeric NPS (positive-class F1)")
    ax.bar_label(b1, fmt="%.3f", padding=3, fontsize=7, color=INK2)
    for bar, v in zip(b2, hn_vals):
        if np.isnan(v):
            ax.text(0.012, bar.get_y() + bar.get_height() / 2, "not evaluated",
                    va="center", fontsize=6.5, color=MUTED)
        else:
            ax.text(v + 0.012, bar.get_y() + bar.get_height() / 2, f"{v:.3f}",
                    va="center", fontsize=7, color=INK2)
    ax.set_yticks(y)
    ax.set_yticklabels(df.index, fontsize=8.5)
    # Divider + block captions between the API and local groups.
    n_api = int((df["_grp"] == 1).sum())
    if 0 < n_api < len(df):
        ax.axhline(n_api - 0.5, color=AXIS, lw=0.8, ls=(0, (3, 3)))
        ax.text(1.0, n_api - 0.5 + 0.15, "local", ha="right", va="bottom",
                fontsize=7.5, color=MUTED, style="italic")
        ax.text(1.0, n_api - 0.5 - 0.15, "API", ha="right", va="top",
                fontsize=7.5, color=MUTED, style="italic")
    ax.set_xlim(0, 1.0)
    ax.set_xlabel("F1")
    ax.grid(axis="x", lw=0.8, color=GRID)
    ax.set_axisbelow(True)
    _despine(ax)
    ax.legend(loc="lower left", bbox_to_anchor=(0, 1.0), ncol=2, fontsize=7.5)
    title = "LLM classifiers: local vs. API"
    if any(SPLIT_MARK in name for name in df.index):
        title += "\n‡ = evaluated on an outdated test split; not directly comparable"
    ax.set_title(title, fontsize=10.5, loc="left", pad=24)
    fig.tight_layout()
    _save(fig, out_dir, "fig5_llm_comparison")


# --------------------------------------------------------------------------- #
# Figure 6 - numeric value extraction (trustworthy evals only)
# --------------------------------------------------------------------------- #
def fig_value_extraction(selected, out_dir: Path) -> pd.DataFrame | None:
    v_supports = value_test_supports(selected)
    fields = sorted(NPS_VALUE_FIELDS, key=lambda f: -(v_supports.get(f) or 0))
    rows = {}
    for prefix in by_role(selected, "value"):
        rec = selected[prefix]
        if rec["value_stale"]:
            print(f"  skip stale value eval: {CURATED[prefix]['label']}")
            continue
        task = rec["results"].get(TASK_VALUE_CATEGORY, {})
        rows[marked_label(prefix, rec, "value_canonical")] = [
            metric(task.get(f, {}), "correct_value", "f1-score") for f in fields
        ]
    if not rows:
        return None
    frame = pd.DataFrame.from_dict(rows, orient="index", columns=fields)
    frame = frame.loc[frame.mean(axis=1, skipna=True).sort_values(ascending=False).index]
    frame["mean"] = frame[fields].mean(axis=1, skipna=True)

    fig, ax = plt.subplots(figsize=(7.6, 0.55 * len(frame) + 2.1))
    im = _annotated_heatmap(ax, frame)
    ax.set_xticklabels(
        [f"{c}\n(n = {v_supports[c]:.0f})" if c in v_supports else c for c in frame.columns],
        rotation=30, ha="right", fontsize=7.5,
    )
    ax.set_yticklabels(frame.index, fontsize=8.5)
    fig.colorbar(im, ax=ax, fraction=0.03, pad=0.02).set_label("F1 of 'correct value'", fontsize=8)
    ax.set_title(
        "Numeric NPS value extraction per field\n"
        "post-fix evaluations only; n = rows with a ground-truth value (test split)",
        fontsize=10.5, loc="left",
    )
    fig.tight_layout()
    _save(fig, out_dir, "fig6_value_extraction")
    return frame


# --------------------------------------------------------------------------- #
# Figure 7 - quality vs speed trade-off
# --------------------------------------------------------------------------- #
def fig_quality_vs_speed(selected, out_dir: Path) -> None:
    pts = []
    for prefix in by_role(selected, "scatter"):
        rec = selected[prefix]
        if rec.get("cat_canonical") is False:
            continue  # older test split; not comparable on this axis
        cat = rec["results"].get(TASK_NPS_CATEGORY, {})
        t = cat.get("time_per_snippet", np.nan)
        q = np.nanmean([positive_f1(cat.get(l, {})) for l in NPS_CATEGORY_LABELS])
        if np.isnan(t) or np.isnan(q):
            continue
        pts.append({"name": CURATED[prefix]["short"], "approach": CURATED[prefix]["approach"],
                    "time": t, "quality": q, "prod": prefix == "ceedaa3a"})
    df = pd.DataFrame(pts)

    fig, ax = plt.subplots(figsize=(7.2, 4.6))
    for approach, grp in df.groupby("approach"):
        ax.scatter(grp["time"], grp["quality"], s=64,
                   color=APPROACH_COLOR[approach], marker=APPROACH_MARKER[approach],
                   edgecolor="white", linewidth=0.8, zorder=3, label=approach)
    prod = df[df["prod"]]
    if not prod.empty:
        ax.scatter(prod["time"], prod["quality"], s=170, facecolor="none",
                   edgecolor=INK, linewidth=1.1, zorder=4)

    # Deterministic per-point label placement to avoid collisions.
    placement = {
        "Qwen3-Emb-4B (per-prop.)": (-7, 3, "right"),
        "Qwen3-Emb-4B (prod.)": (8, -3, "left"),
        "Qwen3-Emb-0.6B": (7, -10, "left"),
        "all-MiniLM-L6-v2": (-7, 6, "right"),
        "bge-m3 (native)": (-8, 2, "right"),
        "gpt-5.4 (few-shot)": (7, -12, "left"),
        "gpt-5.4-mini": (-8, -3, "right"),
        "Qwen3-8B (think)": (-8, 2, "right"),
        "Qwen3-8B": (8, 2, "left"),
        "Mistral-7B": (8, 2, "left"),
    }
    for _, row in df.iterrows():
        dx, dy, ha = placement.get(row["name"], (7, 4, "left"))
        ax.annotate(row["name"], (row["time"], row["quality"]),
                    textcoords="offset points", xytext=(dx, dy), fontsize=7,
                    color=INK2, ha=ha)

    frontier = df.sort_values("time")
    best, keep = -np.inf, []
    for _, row in frontier.iterrows():
        if row["quality"] > best:
            keep.append((row["time"], row["quality"]))
            best = row["quality"]
    if len(keep) > 1:
        fx, fy = zip(*keep)
        ax.plot(fx, fy, "--", color=MUTED, lw=1.0, zorder=2, label="Pareto frontier")

    ax.set_xscale("log")
    ax.set_xlabel("inference time per snippet on NPS Category [s]  (log scale)")
    ax.set_ylabel("mean positive-class F1 (NPS Category)")
    ax.grid(True, which="both", lw=0.8, color=GRID)
    ax.set_axisbelow(True)
    _despine(ax)
    ax.legend(loc="lower left", bbox_to_anchor=(0, 1.0), ncol=4, fontsize=7.5)
    ax.set_title("Quality vs. speed trade-off\n"
                 "circled = boolean path of the production model (unified SVM class)",
                 fontsize=10.5, loc="left", pad=26)
    fig.text(0.01, -0.02,
             "Local-model timings measured on a single consumer GPU (RTX 5070 Ti 16 GB); "
             "large local models were partially memory-constrained.",
             fontsize=6.5, color=MUTED)
    fig.tight_layout()
    _save(fig, out_dir, "fig7_quality_vs_speed")


# --------------------------------------------------------------------------- #
# Figure 8 - production head-to-head: Qwen3-Emb-4B vs bge-m3, same pipeline idea
# --------------------------------------------------------------------------- #
def fig_production_head_to_head(selected, out_dir: Path) -> None:
    """Accuracy per task + speed for the two unified NPS-All configurations."""
    metrics = {}
    for prefix in PROD_PAIR:
        rec = selected.get(prefix)
        if rec is None:
            return
        cat = rec["results"].get(TASK_NPS_CATEGORY, {})
        hn = rec["results"].get(TASK_HAS_NUMERIC, {}).get("has_numeric_nps", {})
        val = rec["results"].get(TASK_VALUE_CATEGORY, {})
        t = cat.get("time_per_snippet", np.nan)
        metrics[prefix] = {
            "NPS Category\n(mean pos. F1, 7 labels)": np.nanmean(
                [positive_f1(cat.get(l, {})) for l in NPS_CATEGORY_LABELS]
            ),
            "Has Numeric NPS\n(pos. F1)": positive_f1(hn),
            "Value extraction\n(mean correct-value F1)": np.nanmean(
                [metric(val.get(f, {}), "correct_value", "f1-score") for f in NPS_VALUE_FIELDS]
            ),
            "_time": t,
        }

    task_names = [k for k in next(iter(metrics.values())) if not k.startswith("_")]
    x = np.arange(len(task_names))
    width = 0.32
    colors = [C1_BLUE, C2_AQUA]
    fig, ax = plt.subplots(figsize=(7.0, 3.9))
    for i, prefix in enumerate(PROD_PAIR):
        vals = [metrics[prefix][t] for t in task_names]
        offset = (i - 0.5) * width
        label = f"{CURATED[prefix]['short']}  ({metrics[prefix]['_time']:.2f} s/snippet)"
        bars = ax.bar(x + offset, vals, width * 0.94, color=colors[i], label=label)
        ax.bar_label(bars, fmt="%.3f", padding=3, fontsize=8, color=INK2)
    ax.set_xticks(x)
    ax.set_xticklabels(task_names, fontsize=8.5)
    ax.set_ylim(0, 1.0)
    ax.set_ylabel("F1")
    ax.grid(axis="y", lw=0.8, color=GRID)
    ax.set_axisbelow(True)
    _despine(ax)
    ax.legend(loc="lower left", bbox_to_anchor=(0, 1.0), ncol=2, fontsize=8)
    ax.set_title(
        "Production head-to-head on NPS All (unified pipeline, joint timing)",
        fontsize=10.5, loc="left", pad=24,
    )
    fig.tight_layout()
    _save(fig, out_dir, "fig8_production_head_to_head")


# --------------------------------------------------------------------------- #
# Summary CSV
# --------------------------------------------------------------------------- #
def write_summary(selected, out_dir: Path) -> pd.DataFrame:
    rows = []
    for prefix, meta in CURATED.items():
        if prefix not in selected:
            continue
        rec = selected[prefix]
        cat = rec["results"].get(TASK_NPS_CATEGORY, {})
        hn = rec["results"].get(TASK_HAS_NUMERIC, {}).get("has_numeric_nps")
        val = rec["results"].get(TASK_VALUE_CATEGORY, {})
        val_f1 = (
            np.nanmean([metric(val.get(f, {}), "correct_value", "f1-score") for f in NPS_VALUE_FIELDS])
            if val and not rec["value_stale"] else np.nan
        )
        rows.append({
            "model": meta["label"],
            "approach": meta["approach"],
            "config_hash": rec["hash"][:12],
            "nps_category_mean_pos_f1": np.nanmean([positive_f1(cat.get(l, {})) for l in NPS_CATEGORY_LABELS]) if cat else np.nan,
            "nps_category_mean_macro_f1": np.nanmean([macro_f1(cat.get(l, {})) for l in NPS_CATEGORY_LABELS]) if cat else np.nan,
            "has_numeric_pos_f1": positive_f1(hn) if hn else np.nan,
            "has_numeric_accuracy": accuracy(hn) if hn else np.nan,
            "value_mean_correct_f1": val_f1,
            "value_eval_stale": bool(val) and rec["value_stale"],
            "cat_split_canonical": rec.get("cat_canonical"),
            "value_split_canonical": rec.get("value_canonical"),
            "time_per_snippet_s": cat.get("time_per_snippet", val.get("time_per_snippet", np.nan) if val else np.nan),
        })
    df = pd.DataFrame(rows).sort_values(
        ["approach", "nps_category_mean_pos_f1"], ascending=[True, False], na_position="last"
    )
    df.to_csv(out_dir / "paper_summary.csv", index=False, float_format="%.4f")
    print("  wrote paper_summary.csv")
    return df


# --------------------------------------------------------------------------- #
# FINAL paper figures (written to <repo>/paper_figures/)
#
# One row per *model* (config description only where a model appears with two
# configs), canonical-split evals only. The headline quality metric is the
# support-weighted mean F1: every property contributes proportionally to its
# positive/value support in the test split, so near-empty classes (n = 1..2)
# cannot dominate the average the way they do in an unweighted mean.
# --------------------------------------------------------------------------- #
REPO_ROOT = SCRIPT_DIR.parent
FINAL_OUT_DIR = REPO_ROOT / "paper_figures"

BOOLEAN_PROPS = NPS_CATEGORY_LABELS + ["has_numeric_nps"]

# (hash prefix, paper label, approach) — one representative config per model.
FINAL_MODELS: list[tuple[str, str, str]] = [
    ("ceedaa3a", "Qwen3-Emb-4B (production)", "Embedding + SVM"),
    ("c7d19631", "Qwen3-Emb-4B (per-property)", "Embedding + SVM"),
    ("4d76a3d5", "Qwen3-Emb-0.6B", "Embedding + SVM"),
    ("4df73844", "bge-m3", "Embedding + SVM"),
    ("1c5568c0", "bge-large-en-v1.5", "Embedding + SVM"),
    ("c7d25c71", "all-MiniLM-L6-v2", "Embedding + SVM"),
    ("600438fa", "para-multi-MiniLM-L12-v2", "Embedding + SVM"),
    ("71e39d0c", "para-multi-mpnet-base-v2", "Embedding + SVM"),
    ("6bc7884b", "Qwen3-8B", "Local LLM"),
    ("c0e8d13d", "gpt-5.4", "API LLM"),
    ("c8c1da99", "gpt-5.4-mini", "API LLM"),
]


def _bool_report(rec: dict, prop: str) -> dict:
    if prop == "has_numeric_nps":
        return rec["results"].get(TASK_HAS_NUMERIC, {}).get("has_numeric_nps") or {}
    return rec["results"].get(TASK_NPS_CATEGORY, {}).get(prop) or {}


def select_final(records: list[dict]) -> list[dict]:
    """Resolve FINAL_MODELS against the eval corpus with per-task validity."""
    final = []
    for prefix, label, approach in FINAL_MODELS:
        rec = next((r for r in records if r["hash"].startswith(prefix)), None)
        if rec is None:
            print(f"  WARNING: final model config not found: {prefix} ({label})")
            continue
        _flag_splits(rec)
        final.append({
            "label": label,
            "approach": approach,
            "rec": rec,
            # booleans valid on the canonical split
            "bool_ok": rec["cat_canonical"] is True,
            # numerics valid: canonical split AND post-NaN-fix evaluation
            "num_ok": rec["value_canonical"] is True and not rec["value_stale"],
        })
    return final


def weighted_mean_f1(f1_by_prop: dict[str, float], weights: dict[str, float]) -> float:
    num = den = 0.0
    for prop, f1 in f1_by_prop.items():
        w = weights.get(prop)
        if f1 is None or np.isnan(f1) or not w or np.isnan(w):
            continue
        num += f1 * w
        den += w
    return num / den if den else float("nan")


def _final_frames(final, supports, v_supports):
    """Per-model F1 dicts for boolean / numeric properties (None = not valid)."""
    for entry in final:
        rec = entry["rec"]
        entry["bool_f1"] = (
            {p: positive_f1(_bool_report(rec, p)) for p in BOOLEAN_PROPS}
            if entry["bool_ok"] else None
        )
        val = rec["results"].get(TASK_VALUE_CATEGORY, {})
        entry["num_f1"] = (
            {f: metric(val.get(f, {}), "correct_value", "f1-score") for f in NPS_VALUE_FIELDS}
            if entry["num_ok"] and val else None
        )
        bool_w = weighted_mean_f1(entry["bool_f1"], supports) if entry["bool_f1"] else np.nan
        num_w = weighted_mean_f1(entry["num_f1"], v_supports) if entry["num_f1"] else np.nan
        all_w = np.nan
        if entry["bool_f1"] and entry["num_f1"]:
            combined = dict(entry["bool_f1"]) | dict(entry["num_f1"])
            all_weights = dict(supports) | dict(v_supports)
            all_w = weighted_mean_f1(combined, all_weights)
        entry["wmean"] = {"boolean": bool_w, "numeric": num_w, "all": all_w}
    return final


def final_heatmap(final, supports, v_supports, variant: str, out_dir: Path) -> None:
    """Per-property F1 heatmap over the final model set.

    variant: "boolean" (8 boolean props), "numeric" (6 value fields) or "all".
    The trailing column is the support-weighted mean over the shown properties.
    """
    if variant == "boolean":
        cols = sorted(BOOLEAN_PROPS, key=lambda p: -supports[p])
        col_w, key = supports, "bool_f1"
        rows = [e for e in final if e["bool_ok"]]
    elif variant == "numeric":
        cols = sorted(NPS_VALUE_FIELDS, key=lambda f: -v_supports[f])
        col_w, key = v_supports, "num_f1"
        rows = [e for e in final if e["num_ok"]]
    else:
        cols = sorted(BOOLEAN_PROPS, key=lambda p: -supports[p]) + \
               sorted(NPS_VALUE_FIELDS, key=lambda f: -v_supports[f])
        col_w = dict(supports) | dict(v_supports)
        key = None
        rows = [e for e in final if e["bool_ok"] or e["num_ok"]]

    data = {}
    for e in rows:
        if variant == "all":
            vals = [(e["bool_f1"] or {}).get(c, np.nan) if c in BOOLEAN_PROPS
                    else (e["num_f1"] or {}).get(c, np.nan) for c in cols]
        else:
            vals = [(e[key] or {}).get(c, np.nan) for c in cols]
        data[e["label"]] = vals + [e["wmean"][variant]]
    frame = pd.DataFrame.from_dict(data, orient="index", columns=cols + ["weighted mean"])
    frame = frame.sort_values("weighted mean", ascending=False, na_position="last")

    fig, ax = plt.subplots(
        figsize=(1.05 + 0.62 * (len(cols) + 1) + 2.4, 0.42 * len(frame) + 2.3)
    )
    im = _annotated_heatmap(ax, frame)
    ax.set_xticklabels(
        [f"{c}\n(n = {col_w[c]:.0f})" if c in col_w else c for c in frame.columns],
        rotation=38, ha="right", fontsize=7,
    )
    ax.set_yticklabels(frame.index, fontsize=8.5)
    fig.colorbar(im, ax=ax, fraction=0.025, pad=0.02).set_label("F1", fontsize=8)
    titles = {
        "boolean": "Boolean properties - positive-class F1 per label",
        "numeric": "Numeric value extraction - F1 of the correct value per field",
        "all": "All 14 properties - F1 per property",
    }
    ax.set_title(
        f"{titles[variant]}\n"
        "weighted mean = support-weighted over the shown properties; "
        "columns sorted by test-split support (n)",
        fontsize=10.5, loc="left",
    )
    fig.tight_layout()
    _save(fig, out_dir, f"final_f1_per_property_{variant}")


def final_support_vs_f1(final, supports, v_supports, out_dir: Path) -> None:
    """Support vs quality funnel over the fully evaluated models.

    One point per (model, property) for the models with full valid coverage
    (the same set as the quality-vs-speed figure); a light range bar spans the
    min-max F1 across those models per property. The funnel shape - tight
    agreement on frequent properties, F1 anywhere between 0 and 1 on the rare
    ones - is the visual argument for the support-weighted mean.
    """
    full = [e for e in final if e["bool_f1"] and e["num_f1"]]
    props = [(p, supports[p], "bool_f1", "o") for p in BOOLEAN_PROPS] +             [(f, v_supports[f], "num_f1", "D") for f in NPS_VALUE_FIELDS]
    props.sort(key=lambda t: t[1])

    short = {
        "KPI_CURRENT_VALUE": "CURRENT VALUE", "KPI_TREND": "TREND",
        "KPI_HISTORICAL_COMPARISON": "HIST. COMP.", "TARGET_OUTLOOK": "TARGET OUTLOOK",
        "NPS_GOAL_REACHED": "GOAL REACHED", "METHODOLOGY_DEFINITION": "METHOD. DEF.",
        "QUALITATIVE_ONLY": "QUAL. ONLY", "has_numeric_nps": "HAS NUMERIC",
        "nps_value_fix": "value_fix", "nps_competition_industry": "competition",
        "nps_value_over": "value_over", "nps_value_below": "value_below",
        "nps_goal_value": "goal_value", "nps_goal_change": "goal_change",
    }

    fig, ax = plt.subplots(figsize=(7.4, 4.6))
    blend = mtransforms.blended_transform_factory(ax.transData, ax.transAxes)

    # Properties with (near-)coinciding supports are dodged as whole columns
    # (range bar, points and label move together, so everything stays aligned).
    dodge = {
        "nps_value_below": 0.78, "NPS_GOAL_REACHED": 1.28,
        "TARGET_OUTLOOK": 0.84, "nps_competition_industry": 1.22,
        "nps_value_fix": 0.86, "has_numeric_nps": 1.14,
    }
    x_display = {prop: x * dodge.get(prop, 1.0) for prop, x, _k, _m in props}

    for prop, _x, key, _marker in props:
        xd = x_display[prop]
        vals = [e[key].get(prop, np.nan) for e in full]
        vals = [v for v in vals if not np.isnan(v)]
        if vals:
            ax.plot([xd, xd], [min(vals), max(vals)], color=GRID, lw=2.4,
                    solid_capstyle="round", zorder=1)
        ax.text(xd, 1.03, short.get(prop, prop), rotation=90,
                transform=blend, ha="center", va="bottom", fontsize=6, color=MUTED)

    seen = set()
    for j, e in enumerate(full):
        jitter = 1.0 + (j - (len(full) - 1) / 2) * 0.022
        for key, marker in (("bool_f1", "o"), ("num_f1", "D")):
            xs, ys = [], []
            for prop, _x, k, _m in props:
                if k != key:
                    continue
                f1 = e[key].get(prop, np.nan)
                if not np.isnan(f1):
                    xs.append(x_display[prop] * jitter)
                    ys.append(f1)
            label = e["approach"] if e["approach"] not in seen else None
            if label:
                seen.add(e["approach"])
            ax.scatter(xs, ys, s=34, color=APPROACH_COLOR[e["approach"]], marker=marker,
                       edgecolor="white", linewidth=0.5, alpha=0.95, zorder=3, label=label)

    ax.set_xscale("log")
    ax.set_xlabel("support in test split (log scale)")
    ax.set_ylabel("F1 (positive class / correct value)")
    ax.set_ylim(-0.04, 1.04)
    ax.grid(axis="y", lw=0.8, color=GRID)
    ax.set_axisbelow(True)
    _despine(ax)
    from matplotlib.lines import Line2D
    handles, labels = ax.get_legend_handles_labels()
    handles += [Line2D([], [], marker="o", ls="", color=MUTED, label="boolean property"),
                Line2D([], [], marker="D", ls="", color=MUTED, label="numeric field")]
    labels += ["boolean property", "numeric field"]
    ax.legend(handles, labels, loc="upper left", bbox_to_anchor=(0.02, 0.98),
              fontsize=7, ncol=1)
    ax.set_title("Support vs. quality - all 14 properties, fully evaluated models\n"
                 "bars span the min-max F1 across the six models",
                 fontsize=10.5, loc="left", pad=72)
    fig.tight_layout()
    _save(fig, out_dir, "final_support_vs_f1")


def final_quality_vs_speed(final, out_dir: Path) -> None:
    """Support-weighted mean F1 over ALL 14 properties vs joint inference time."""
    pts = []
    for e in final:
        q = e["wmean"]["all"]
        t = e["rec"]["results"].get(TASK_NPS_CATEGORY, {}).get("time_per_snippet", np.nan)
        if np.isnan(q) or np.isnan(t):
            continue
        pts.append({"label": e["label"], "approach": e["approach"], "time": t, "quality": q,
                    "prod": e["rec"]["hash"].startswith("ceedaa3a")})
    df = pd.DataFrame(pts)

    fig, ax = plt.subplots(figsize=(7.0, 4.6))
    for approach, grp in df.groupby("approach"):
        ax.scatter(grp["time"], grp["quality"], s=70, color=APPROACH_COLOR[approach],
                   marker=APPROACH_MARKER[approach], edgecolor="white", linewidth=0.8,
                   zorder=3, label=approach)
    prod = df[df["prod"]]
    if not prod.empty:
        ax.scatter(prod["time"], prod["quality"], s=190, facecolor="none",
                   edgecolor=INK, linewidth=1.1, zorder=4)

    placement = {
        "Qwen3-Emb-4B (production)": (9, -3, "left"),
        "Qwen3-Emb-0.6B": (7, -11, "left"),
        "bge-m3": (2, 8, "left"),
        "Qwen3-8B": (-8, 2, "right"),
        "gpt-5.4-mini": (-8, -4, "right"),
    }
    for _, row in df.iterrows():
        dx, dy, ha = placement.get(row["label"], (7, 4, "left"))
        ax.annotate(row["label"], (row["time"], row["quality"]),
                    textcoords="offset points", xytext=(dx, dy), fontsize=7.5,
                    color=INK2, ha=ha)

    frontier = df.sort_values("time")
    best, keep = -np.inf, []
    for _, row in frontier.iterrows():
        if row["quality"] > best:
            keep.append((row["time"], row["quality"]))
            best = row["quality"]
    if len(keep) > 1:
        fx, fy = zip(*keep)
        ax.plot(fx, fy, "--", color=MUTED, lw=1.0, zorder=2, label="Pareto frontier")

    ax.set_xscale("log")
    ax.set_xlabel("inference time per snippet, all 14 properties jointly [s]  (log scale)")
    ax.set_ylabel("support-weighted mean F1 (all 14 properties)")
    ax.grid(True, which="both", lw=0.8, color=GRID)
    ax.set_axisbelow(True)
    _despine(ax)
    ax.legend(loc="lower right", fontsize=8)
    ax.set_title("Quality vs. speed - all comparable models with full coverage\n"
                 "circled = production model", fontsize=10.5, loc="left")
    fig.text(0.01, -0.02,
             "Local-model timings measured on a single consumer GPU (RTX 5070 Ti 16 GB).",
             fontsize=6.5, color=MUTED)
    fig.tight_layout()
    _save(fig, out_dir, "final_quality_vs_speed")


def render_final_figures(records, supports, v_supports) -> None:
    FINAL_OUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Writing FINAL paper figures to: {FINAL_OUT_DIR}")
    final = _final_frames(select_final(records), supports, v_supports)
    for variant in ("boolean", "numeric", "all"):
        final_heatmap(final, supports, v_supports, variant, FINAL_OUT_DIR)
    final_support_vs_f1(final, supports, v_supports, FINAL_OUT_DIR)
    final_quality_vs_speed(final, FINAL_OUT_DIR)


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--config-dir", type=Path, default=DEFAULT_CONFIG_DIR)
    parser.add_argument("--out-dir", type=Path, default=None)
    args = parser.parse_args()

    config_dir = args.config_dir.resolve()
    out_dir = (args.out_dir or config_dir / "graphics" / "paper").resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    _style()

    records = load_models(config_dir)
    selected = select_curated(records)
    supports = test_supports(selected)

    print(f"Writing paper figures to: {out_dir}")
    fig_dataset_composition(out_dir)
    fig_headline_per_label(selected, supports, out_dir)
    fig_support_vs_f1(selected, supports, out_dir)
    fig_embedding_backbones(selected, out_dir)
    fig_llm_comparison(selected, out_dir)
    fig_value_extraction(selected, out_dir)
    fig_quality_vs_speed(selected, out_dir)
    fig_production_head_to_head(selected, out_dir)
    summary = write_summary(selected, out_dir)

    render_final_figures(records, supports, value_test_supports(selected))

    print("\nCurated summary:")
    with pd.option_context("display.max_columns", None, "display.width", 220):
        print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
