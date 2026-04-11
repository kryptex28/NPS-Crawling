"""Pre-processing pipeline to clean, filter, score similarity, and store data."""

import json
import logging
import os
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from tqdm import tqdm

from nps_crawling.config import Config
from nps_crawling.db.db_adapter import DbAdapter

from .cleaning import CleanTextPipeline
from .filtering import NpsMentionFilterPipeline
from .similarity import SimilarityPipeline
from .storage import SaveToJSONPipeline

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Multiprocessing worker helpers (module-level for pickling on Windows/spawn)
# ---------------------------------------------------------------------------

_worker_cleaner = None
_worker_filter = None


def _init_worker():
    """Create per-process cleaner and filter instances (called once per worker)."""
    global _worker_cleaner, _worker_filter  # noqa: PLW0603
    _worker_cleaner = CleanTextPipeline()
    _worker_filter = NpsMentionFilterPipeline()


def _process_single_file(file_path):
    """Load, clean, and filter one JSON file.

    Returns ``(file_path, records)`` on success, or ``None`` on error / empty.
    ``core_text`` is dropped from every record before returning to free memory.
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            records = json.load(f)
    except json.JSONDecodeError:
        return None

    if not records:
        return None

    records = _worker_cleaner.cleaning_workflow(records)
    records = _worker_filter.filtering_workflow(records)

    # core_text is no longer needed after filtering — drop it to save memory
    # during IPC serialisation and while records sit in the chunk buffer.
    for record in records:
        record.pop("core_text", None)

    return (file_path, records)


class PreProcessingPipeline(Config):
    """Pre-processing pipeline class to clean, filter, and store data.

    Pipeline per file
    -----------------
    1. **Clean** – HTML/XML → plain text.
    2. **Filter** – extract context windows around NPS-related phrases.
    3. **Score** – semantic similarity of each window against a reference text.
    4. **Split** – splits contexts based on threshold.
    5. **Store** – high-scoring contexts go to ``json_processed/``; low-scoring
       contexts go to ``json_reject/``. Both are saved.
    """

    # Number of files per processing chunk.  Controls peak memory: all
    # cleaned/filtered records for one chunk are held in RAM while their
    # context windows are batch-embedded on the GPU.
    FILES_PER_CHUNK = 1000

    def __init__(self):
        """Initialize the PreProcessingPipeline."""
        self.json_raw_dir = Config.RAW_JSON_PATH_CRAWLER / "files"

        # Create version-specific directories on demand
        Config.NPS_CONTEXT_JSON_PATH.mkdir(parents=True, exist_ok=True)
        (Config.NPS_CONTEXT_JSON_PATH / "files").mkdir(parents=True, exist_ok=True)
        Config.NPS_REJECTED_JSON_PATH.mkdir(parents=True, exist_ok=True)
        (Config.NPS_REJECTED_JSON_PATH / "files").mkdir(parents=True, exist_ok=True)

        self.similarity = SimilarityPipeline()
        self.storage = SaveToJSONPipeline()

        self._keyword_filter = Config.SINGLE_KEYWORD_FILTER
        self._db = DbAdapter() if self._keyword_filter else None

    def pre_processing_workflow(self):
        """Run the full pre-processing workflow over all raw JSON files."""
        start_time = time.time()

        json_files = sorted(self.json_raw_dir.glob("*.json"))
        if not json_files:
            logger.info("No raw JSON files found to process")
            return None

        # Pre-filter files when the single-keyword filter is active.
        # This path is sequential (needs DB access) but is a rare-use option.
        if self._keyword_filter and self._db:
            json_files = self._pre_filter_files(json_files)
            if not json_files:
                logger.info("No files passed the keyword filter")
                return None

        # Determine worker count — leave one core free for the main process.
        max_workers = max(1, (os.cpu_count() or 1) - 1)
        logger.info(
            "Starting preprocessing: %d files, %d CPU workers, chunk_size=%d",
            len(json_files), max_workers, self.FILES_PER_CHUNK,
        )

        # ---- Aggregate statistics ----
        filings_total = 0
        filings_accepted = 0
        filings_accepted_fully = 0
        filings_rejected = 0
        filings_rejected_fully = 0
        total_context_windows_accepted = 0
        total_context_windows_rejected = 0
        all_similarity_scores = []
        all_filings_averages = []

        total_files = len(json_files)
        progress = tqdm(total=total_files, desc="Pre-processing documents", unit="file")

        for chunk_start in range(0, total_files, self.FILES_PER_CHUNK):
            chunk_files = json_files[chunk_start : chunk_start + self.FILES_PER_CHUNK]

            # ----------------------------------------------------------
            # Phase 1: Parallel clean + filter (CPU-bound, multiprocess)
            # ----------------------------------------------------------
            file_results = []  # list of (Path, records_list)
            with ProcessPoolExecutor(
                max_workers=max_workers,
                initializer=_init_worker,
            ) as pool:
                for result in pool.map(_process_single_file, chunk_files):
                    progress.update(1)
                    if result is not None:
                        file_results.append(result)

            if not file_results:
                continue

            # ----------------------------------------------------------
            # Phase 2: Batch-embed all context windows in this chunk
            # ----------------------------------------------------------
            all_texts = []
            index_map = []  # (file_result_idx, record_idx, context_idx)

            for fr_idx, (_path, records) in enumerate(file_results):
                for rec_idx, record in enumerate(records):
                    if "metadata" not in record:
                        record["metadata"] = {}
                    record["metadata"]["experiment"] = Config.PREPROCESSING_VERSION
                    contexts = record.get("context", [])
                    record["metadata"]["Context Windows total"] = len(contexts)
                    if not contexts:
                        record["metadata"]["Context Windows Accept"] = 0
                        record["metadata"]["Context Windows Reject"] = 0
                        continue
                    for ctx_idx, ctx in enumerate(contexts):
                        all_texts.append(ctx["context"])
                        index_map.append((fr_idx, rec_idx, ctx_idx))

            if all_texts:
                all_scores = self.similarity.embed_and_score(all_texts)
                for i, (fr_idx, rec_idx, ctx_idx) in enumerate(index_map):
                    file_results[fr_idx][1][rec_idx]["context"][ctx_idx][
                        "similarity_score"
                    ] = round(float(all_scores[i]), 4)

            # ----------------------------------------------------------
            # Phase 3: Per-file metadata, split, store, collect stats
            # ----------------------------------------------------------
            for file_path, records in file_results:
                self.similarity.compute_record_metadata(records)
                accepted_records, rejected_records = self.similarity.split_records(
                    records,
                )

                self.storage.storage_workflow(
                    accepted_records,
                    source_filename=Path(file_path).stem,
                    reject=False,
                    update_db=True,
                )
                self.storage.storage_workflow(
                    rejected_records,
                    source_filename=Path(file_path).stem,
                    reject=True,
                    update_db=False,
                )

                # Collect per-record statistics
                for record in records:
                    meta = record.get("metadata", {})
                    cw_accept = meta.get("Context Windows Accept", 0)
                    cw_reject = meta.get("Context Windows Reject", 0)
                    cw_total = meta.get("Context Windows total", 0)

                    if cw_total == 0:
                        continue

                    filings_total += 1
                    total_context_windows_accepted += cw_accept
                    total_context_windows_rejected += cw_reject

                    if cw_accept > 0:
                        filings_accepted += 1
                    if cw_accept == cw_total:
                        filings_accepted_fully += 1
                    if cw_reject > 0:
                        filings_rejected += 1
                    if cw_reject == cw_total:
                        filings_rejected_fully += 1

                    for ctx in record.get("context", []):
                        if "similarity_score" in ctx:
                            all_similarity_scores.append(ctx["similarity_score"])

                    if "filings_average" in record:
                        all_filings_averages.append(record["filings_average"])

            # Free chunk data before processing the next chunk
            del file_results, all_texts, index_map

        progress.close()
        elapsed_seconds = round(time.time() - start_time, 2)

        # ---- Write experiment summary JSON ----
        summary = {
            "preprocessing_duration_seconds": elapsed_seconds,
            "experiment_setup": {
                "preprocessing_version": Config.PREPROCESSING_VERSION,
                "filter_phrases": Config.LIST_OF_PHRASES_TO_FILTER_FILINGS_FOR,
                "context_sentences_before": Config.AMOUNT_SENTENCES_INCLUDED_BEFORE,
                "context_sentences_after": Config.AMOUNT_SENTENCES_INCLUDED_AFTER,
                "embedding_model": Config.SIMILARITY_EMBEDDING_MODEL,
                "similarity_reference_text": Config.SIMILARITY_REFERENCE_TEXT,
                "similarity_threshold": Config.SIMILARITY_THRESHOLD_CONTEXT_WINDOW,
                "single_keyword_filter": Config.SINGLE_KEYWORD_FILTER,
            },
            "processed_filings": {
                "filings_processed_total": filings_total,
                "filings_accepted_total": filings_accepted,
                "filings_accepted_full": filings_accepted_fully,
                "filings_accepted_partial": filings_accepted - filings_accepted_fully,
                "filings_rejected_total": filings_rejected,
                "filings_rejected_full": filings_rejected_fully,
                "filings_rejected_partial": filings_rejected - filings_rejected_fully,
                "context_windows_accepted": total_context_windows_accepted,
                "context_windows_rejected": total_context_windows_rejected,
                "lowest_similarity_context": round(min(all_similarity_scores), 4) if all_similarity_scores else None,
                "highest_similarity_context": round(max(all_similarity_scores), 4) if all_similarity_scores else None,
                "average_similarity_context": round(sum(all_similarity_scores) / len(all_similarity_scores), 4) if all_similarity_scores else None,
                "lowest_similarity_filing": round(min(all_filings_averages), 4) if all_filings_averages else None,
                "highest_similarity_filing": round(max(all_filings_averages), 4) if all_filings_averages else None,
                "average_similarity_filing": round(sum(all_filings_averages) / len(all_filings_averages), 4) if all_filings_averages else None,
            },
        }

        summary_path = Config.NPS_CONTEXT_JSON_PATH / f"preprocessing_{Config.PREPROCESSING_VERSION}.json"
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)

        if all_similarity_scores:
            plt.figure(figsize=(10, 6))
            N, bins, patches = plt.hist(all_similarity_scores, bins=50, edgecolor='black')

            for i in range(len(patches)):
                bin_mid = (bins[i] + bins[i + 1]) / 2
                if bin_mid < Config.SIMILARITY_THRESHOLD_CONTEXT_WINDOW:
                    patches[i].set_facecolor('red')
                else:
                    patches[i].set_facecolor('skyblue')

            title_main = f"Similarity Score Distribution (Experiment: {Config.PREPROCESSING_VERSION})"
            title_sub = f"context_windows_accepted: {total_context_windows_accepted}, context_windows_rejected: {total_context_windows_rejected}"
            plt.title(f"{title_main}\n{title_sub}", fontsize=12)

            plt.axvline(Config.SIMILARITY_THRESHOLD_CONTEXT_WINDOW, color='darkred', linestyle='dashed', linewidth=2, label='Threshold')
            plt.legend()

            plt.xlabel("Similarity Score")
            plt.ylabel("Frequency")
            plt.grid(axis='y', alpha=0.75)
            plot_path = Config.NPS_CONTEXT_JSON_PATH / "similarity_score_distribution.png"
            plt.savefig(plot_path)
            plt.close()
            logger.info("Saved similarity score distribution plot to %s", plot_path)

        logger.info("Experiment summary written to %s", summary_path)
        logger.info(
            "Finished preprocessing experiment '%s'. "
            "Filings: %d total, %d accepted (%d full, %d partial), "
            "%d rejected (%d full, %d partial). "
            "Context windows: %d accepted, %d rejected.",
            Config.PREPROCESSING_VERSION,
            filings_total,
            filings_accepted, filings_accepted_fully, filings_accepted - filings_accepted_fully,
            filings_rejected, filings_rejected_fully, filings_rejected - filings_rejected_fully,
            total_context_windows_accepted, total_context_windows_rejected,
        )

        return None

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _pre_filter_files(self, json_files):
        """Filter files by single-keyword DB check (sequential).

        Only used when ``SINGLE_KEYWORD_FILTER`` is set.  Loads each file to
        extract the filing ID, then queries the DB for its keywords.
        """
        filtered = []
        for json_file in tqdm(json_files, desc="Checking keyword filter", unit="file"):
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    records = json.load(f)
            except json.JSONDecodeError:
                continue
            if not records:
                continue
            filing_id = records[0].get("metadata", {}).get("filing", {}).get("id")
            if not filing_id:
                logger.warning("No filing id in %s — skipping", json_file.name)
                continue
            raw_keywords = self._db.return_keywords(filing_id)
            cleaned_keywords = [k.strip("\"'") for k in raw_keywords]
            if cleaned_keywords == [self._keyword_filter]:
                filtered.append(json_file)
            else:
                logger.debug(
                    "Skipping %s — keywords %s don't match single-keyword filter '%s'",
                    json_file.name, cleaned_keywords, self._keyword_filter,
                )
        logger.info(
            "Keyword filter: %d / %d files passed", len(filtered), len(json_files),
        )
        return filtered
