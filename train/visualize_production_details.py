"""Detail figures for the production model (unified SVM on Qwen3-Embedding-4B).

Reconstructs the boolean-path predictions and SVM decision scores on the
canonical evaluation split (shared-instruction embeddings + cached per-property SVMs
from ``cache/Qwen3-Embedding-4B/shared/``) and renders four insight figures to
``<repo>/paper_figures/``:

* ``prod_precision_recall``  - precision vs recall per property (all 14;
  numeric fields taken from the stored NPS All evaluation).
* ``prod_confusion_matrices`` - 2x2 confusion matrix per boolean property.
* ``prod_pr_curves``          - precision-recall curve per boolean property
  from the SVM decision function, current operating point marked.
* ``prod_error_histogram``    - number of wrong boolean labels per snippet.

Run with::

    KMP_DUPLICATE_LIB_OK=TRUE python train/visualize_production_details.py
"""

from __future__ import annotations

import os

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

import json
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from visualize_paper_evaluation import (  # noqa: E402  (also selects Agg backend)
    AXIS,
    BOOLEAN_PROPS,
    C1_BLUE,
    C2_AQUA,
    FINAL_OUT_DIR,
    GRID,
    GROUND_TRUTH_CSV,
    INK,
    INK2,
    MUTED,
    NPS_VALUE_FIELDS,
    SEQ_BLUE,
    _despine,
    _save,
    _style,
)

import matplotlib.pyplot as plt  # noqa: E402

from nps_crawling.classification.models.model import ground_truth_train_test_split  # noqa: E402
from nps_crawling.classification.models.qwen_advanced import QWEN_Advanced  # noqa: E402
from nps_crawling.config import Config  # noqa: E402

PROD_EVAL_JSON = (
    Config.CLASSIFICATION_CONFIG_DIR / "Qwen3-Embedding-4B"
    / "ceedaa3aba192ca96f31a7404314395025a191a2d72b18c8a0c3e28ea9df5563.json"
)
SVM_DIR = Path(Config.CLASSIFICATION_CACHE_DIR) / "Qwen3-Embedding-4B" / "shared"


# --------------------------------------------------------------------------- #
# Predictions + scores on the canonical evaluation split
# --------------------------------------------------------------------------- #
def compute_predictions():
    df = pd.read_csv(GROUND_TRUTH_CSV)
    _train, test_df = ground_truth_train_test_split(df)
    texts = test_df[Config.CLASSIFICATION_FEW_SHOT_TEXT_COLUMN].astype(str).tolist()

    model = QWEN_Advanced("Qwen/Qwen3-Embedding-4B", optimized="true")
    print(f"embedding {len(texts)} test snippets (shared instruction) ...")
    embeddings = model._embed_texts(texts, model.SHARED_INSTRUCTION)

    y_true, y_pred, scores = {}, {}, {}
    for prop in BOOLEAN_PROPS:
        pipe = joblib.load(SVM_DIR / f"{prop}.joblib")
        y_true[prop] = test_df[prop].astype(int).to_numpy().astype(bool)
        y_pred[prop] = np.asarray([bool(v) for v in pipe.predict(embeddings)])
        scores[prop] = pipe.decision_function(embeddings)
    return y_true, y_pred, scores, len(texts)


# --------------------------------------------------------------------------- #
# Figure 1 - precision vs recall dumbbell (all 14 properties)
# --------------------------------------------------------------------------- #
def fig_precision_recall(y_true, y_pred, out_dir: Path) -> None:
    rows = []
    for prop in BOOLEAN_PROPS:
        t, p = y_true[prop], y_pred[prop]
        tp = int((t & p).sum())
        prec = tp / p.sum() if p.sum() else np.nan
        rec = tp / t.sum() if t.sum() else np.nan
        rows.append((prop, int(t.sum()), prec, rec))

    stored = json.load(open(PROD_EVAL_JSON, encoding="utf-8"))
    block = stored["evaluation_results"]["NPS All"]
    for field in NPS_VALUE_FIELDS:
        cv = (block.get(field) or {}).get("correct_value") or {}
        rows.append((field, int(cv.get("support", 0)),
                     cv.get("precision", np.nan), cv.get("recall", np.nan)))

    rows.sort(key=lambda r: r[1])
    y = np.arange(len(rows))
    fig, ax = plt.subplots(figsize=(7.0, 0.34 * len(rows) + 1.9))
    for yi, (prop, n, prec, rec) in zip(y, rows):
        ax.plot([prec, rec], [yi, yi], color=GRID, lw=2.0, zorder=1)
        ax.scatter([prec], [yi], s=46, color=C1_BLUE, zorder=3)
        ax.scatter([rec], [yi], s=46, color=C2_AQUA, zorder=3)
    ax.scatter([], [], s=46, color=C1_BLUE, label="precision")
    ax.scatter([], [], s=46, color=C2_AQUA, label="recall")
    ax.set_yticks(y)
    ax.set_yticklabels([f"{prop}  (n = {n})" for prop, n, _p, _r in rows], fontsize=8)
    ax.set_xlim(-0.03, 1.03)
    ax.set_xlabel("positive class / correct value")
    ax.grid(axis="x", lw=0.8, color=GRID)
    ax.set_axisbelow(True)
    _despine(ax)
    ax.legend(loc="lower left", bbox_to_anchor=(0, 1.0), ncol=2, fontsize=8)
    ax.set_title("Production model - precision vs. recall per property\n"
                 "properties sorted by evaluation-split support",
                 fontsize=10.5, loc="left", pad=26)
    fig.tight_layout()
    _save(fig, out_dir, "prod_precision_recall")


# --------------------------------------------------------------------------- #
# Figure 2 - confusion matrix per boolean property
# --------------------------------------------------------------------------- #
def fig_confusion_matrices(y_true, y_pred, out_dir: Path) -> None:
    fig, axes = plt.subplots(2, 4, figsize=(9.6, 5.6), gridspec_kw={"hspace": 0.42})
    for ax, prop in zip(axes.ravel(), BOOLEAN_PROPS):
        t, p = y_true[prop], y_pred[prop]
        cm = np.array([[int((~t & ~p).sum()), int((~t & p).sum())],
                       [int((t & ~p).sum()), int((t & p).sum())]])
        row_norm = cm / np.maximum(cm.sum(axis=1, keepdims=True), 1)
        ax.imshow(row_norm, cmap=SEQ_BLUE, vmin=0, vmax=1)
        for r in range(2):
            for c in range(2):
                shade = "white" if row_norm[r, c] >= 0.6 else INK
                ax.text(c, r, f"{cm[r, c]}\n{row_norm[r, c]:.0%}", ha="center",
                        va="center", fontsize=8, color=shade)
        ax.set_xticks([0, 1], ["pred neg", "pred pos"], fontsize=7)
        ax.set_yticks([0, 1], ["true neg", "true pos"], fontsize=7, rotation=90,
                      va="center")
        if ax not in axes[-1, :]:
            ax.set_xticklabels([])
        ax.tick_params(length=0)
        for side in ax.spines.values():
            side.set_visible(False)
        ax.set_title(f"{prop}\n(n pos = {int(t.sum())})", fontsize=8.5)
    fig.suptitle("Production model - confusion matrices, boolean properties "
                 "(cells: count and share of true class)",
                 fontsize=11, x=0.02, ha="left")
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    _save(fig, out_dir, "prod_confusion_matrices")


# --------------------------------------------------------------------------- #
# Figure 3 - precision-recall curves per boolean property
# --------------------------------------------------------------------------- #
def fig_pr_curves(y_true, y_pred, scores, n_test: int, out_dir: Path) -> None:
    from sklearn.metrics import average_precision_score, precision_recall_curve

    fig, axes = plt.subplots(2, 4, figsize=(10.4, 5.4), sharex=True, sharey=True)
    for ax, prop in zip(axes.ravel(), BOOLEAN_PROPS):
        t, p, s = y_true[prop], y_pred[prop], scores[prop]
        prec, rec, _ = precision_recall_curve(t, s)
        ap = average_precision_score(t, s)
        ax.plot(rec, prec, color=C1_BLUE, lw=1.6, zorder=3)
        # operating point of the deployed threshold (SVM decision boundary)
        tp = int((t & p).sum())
        op_p = tp / p.sum() if p.sum() else 0.0
        op_r = tp / t.sum() if t.sum() else 0.0
        ax.scatter([op_r], [op_p], s=52, facecolor="white", edgecolor=INK,
                   linewidth=1.2, zorder=4)
        ax.axhline(t.sum() / n_test, color=AXIS, lw=0.8, ls=(0, (3, 3)), zorder=1)
        ax.set_title(f"{prop}\nAP = {ap:.2f}   (n pos = {int(t.sum())})", fontsize=8)
        ax.set_xlim(-0.03, 1.03)
        ax.set_ylim(-0.03, 1.06)
        ax.grid(lw=0.8, color=GRID)
        ax.set_axisbelow(True)
        _despine(ax)
    for ax in axes[-1, :]:
        ax.set_xlabel("recall", fontsize=8)
    for ax in axes[:, 0]:
        ax.set_ylabel("precision", fontsize=8)
    fig.suptitle("Production model - precision-recall curves from the SVM decision scores\n"
                 "circle = deployed operating point; dashed line = positive prevalence",
                 fontsize=11, x=0.02, ha="left")
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    _save(fig, out_dir, "prod_pr_curves")


# --------------------------------------------------------------------------- #
# Figure 4 - wrong boolean labels per snippet
# --------------------------------------------------------------------------- #
def fig_error_histogram(y_true, y_pred, n_test: int, out_dir: Path) -> None:
    errors = np.zeros(n_test, dtype=int)
    for prop in BOOLEAN_PROPS:
        errors += (y_true[prop] != y_pred[prop]).astype(int)
    max_err = int(errors.max())
    counts = np.bincount(errors, minlength=max_err + 1)

    fig, ax = plt.subplots(figsize=(6.6, 3.6))
    x = np.arange(len(counts))
    bars = ax.bar(x, counts, width=0.62, color=C1_BLUE)
    cum = np.cumsum(counts) / n_test
    for xi, bar, c in zip(x, bars, cum):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + n_test * 0.008,
                f"{int(bar.get_height())}\n({c:.0%} ≤ {xi})", ha="center", va="bottom",
                fontsize=7, color=INK2)
    ax.set_xticks(x)
    ax.set_xlabel(f"wrong boolean labels per snippet (of {len(BOOLEAN_PROPS)})")
    ax.set_ylabel("snippets")
    ax.set_ylim(0, counts.max() * 1.25)
    ax.grid(axis="y", lw=0.8, color=GRID)
    ax.set_axisbelow(True)
    _despine(ax)
    exact = counts[0] / n_test
    ax.set_title("Production model - error concentration per snippet\n"
                 f"{exact:.0%} of test snippets have every boolean property correct",
                 fontsize=10.5, loc="left")
    fig.tight_layout()
    _save(fig, out_dir, "prod_error_histogram")


def main() -> None:
    _style()
    FINAL_OUT_DIR.mkdir(parents=True, exist_ok=True)
    y_true, y_pred, scores, n_test = compute_predictions()

    # Sanity: recomputed F1 must match the stored evaluation.
    stored = json.load(open(PROD_EVAL_JSON, encoding="utf-8"))
    rep = stored["evaluation_results"]["NPS All"]["KPI_CURRENT_VALUE"]["True"]
    t, p = y_true["KPI_CURRENT_VALUE"], y_pred["KPI_CURRENT_VALUE"]
    tp = int((t & p).sum())
    f1 = 2 * tp / (t.sum() + p.sum())
    if abs(f1 - rep["f1-score"]) > 1e-6:
        print(f"  WARNING: recomputed F1 {f1:.4f} != stored {rep['f1-score']:.4f}")
    else:
        print(f"  sanity check OK: recomputed KPI_CURRENT_VALUE F1 matches stored ({f1:.4f})")

    print(f"Writing production detail figures to: {FINAL_OUT_DIR}")
    fig_precision_recall(y_true, y_pred, FINAL_OUT_DIR)
    fig_confusion_matrices(y_true, y_pred, FINAL_OUT_DIR)
    fig_pr_curves(y_true, y_pred, scores, n_test, FINAL_OUT_DIR)
    fig_error_histogram(y_true, y_pred, n_test, FINAL_OUT_DIR)


if __name__ == "__main__":
    main()
