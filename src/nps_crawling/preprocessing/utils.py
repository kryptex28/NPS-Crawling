"""Pre-processing pipeline to clean, filter, score similarity, and store data."""

import json
import logging

from tqdm import tqdm

from nps_crawling.config import Config

from .cleaning import CleanTextPipeline
from .filtering import NpsMentionFilterPipeline
from .similarity import SimilarityPipeline
from .storage import SaveToJSONPipeline

logger = logging.getLogger(__name__)


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
    def __init__(self):
        """Initialize the PreProcessingPipeline."""
        self.json_raw_dir = Config.RAW_JSON_PATH_CRAWLER

        self.cleaner = CleanTextPipeline()
        self.filter = NpsMentionFilterPipeline()
        self.similarity = SimilarityPipeline()
        self.storage = SaveToJSONPipeline()

    def pre_processing_workflow(self):
        """Run the full pre-processing workflow over all raw JSON files."""
        json_files = sorted(self.json_raw_dir.glob("*.json"))
        if not json_files:
            logger.info("No raw JSON files found to process")
            return None

        # Aggregate statistics
        filings_total = 0
        filings_accepted = 0          # at least one context window accepted
        filings_accepted_fully = 0    # ALL context windows accepted
        filings_rejected = 0          # at least one context window rejected
        filings_rejected_fully = 0    # ALL context windows rejected
        total_context_windows_accepted = 0
        total_context_windows_rejected = 0

        for json_file in tqdm(json_files, desc="Pre-processing documents", unit="file"):
            with open(json_file, "r", encoding="utf-8") as f:
                records = json.load(f)

            if not records:
                continue

            records = self.cleaner.cleaning_workflow(records)
            records = self.filter.filtering_workflow(records)

            accepted_records, rejected_records = self.similarity.similarity_workflow(records)

            self.storage.storage_workflow(
                accepted_records, source_filename=json_file.stem, reject=False, update_db=True
            )
            self.storage.storage_workflow(
                rejected_records, source_filename=json_file.stem, reject=True, update_db=False
            )

            # Collect per-record statistics from the metadata set by SimilarityPipeline
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

            logger.info("Processed %s (%d records) — SPLIT", json_file.name, len(records))

        # Write experiment summary JSON
        summary = {
            "experiment_setup": {
                "experiment_name": Config.EXPERIMENT_NAME,
                "filter_phrases": Config.LIST_OF_PHRASES_TO_FILTER_FILINGS_FOR,
                "context_sentences_before": Config.AMOUNT_SENTENCES_INCLUDED_BEFORE,
                "context_sentences_after": Config.AMOUNT_SENTENCES_INCLUDED_AFTER,
                "embedding_model": Config.SIMILARITY_EMBEDDING_MODEL,
                "similarity_reference_text": Config.SIMILARITY_REFERENCE_TEXT,
                "similarity_threshold": Config.SIMILARITY_THRESHOLD_CONTEXT_WINDOW,
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
            },
        }

        summary_path = Config.EXPERIMENT_PATH / f"experiment_{Config.EXPERIMENT_NAME}.json"
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)

        logger.info("Experiment summary written to %s", summary_path)
        logger.info(
            "Finished preprocessing experiment '%s'. "
            "Filings: %d total, %d accepted (%d full, %d partial), "
            "%d rejected (%d full, %d partial). "
            "Context windows: %d accepted, %d rejected.",
            Config.EXPERIMENT_NAME,
            filings_total,
            filings_accepted, filings_accepted_fully, filings_accepted - filings_accepted_fully,
            filings_rejected, filings_rejected_fully, filings_rejected - filings_rejected_fully,
            total_context_windows_accepted, total_context_windows_rejected,
        )

        return None
