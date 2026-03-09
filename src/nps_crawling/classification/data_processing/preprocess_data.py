"""Data processing for classification tasks from JSON processed files."""

import json
import re

import pandas as pd

from nps_crawling.config import Config


class ClassificationDataProcessing(Config):
    """Data processing class for classification tasks."""
    def __init__(self):
        """Initialize with path to json_processed/."""
        self.json_processed_root = Config.NPS_CONTEXT_JSON_PATH

    def _parse_display_name(self, display_names):
        """Extract company name and ticker from a display_names list.

        Display names have the format:
            "Company Name (TICKER) (CIK 0001234567)"

        Returns (company, ticker) as strings.
        """
        if not display_names:
            return "Unknown", "N/A"

        raw = display_names[0] if isinstance(display_names, list) else display_names

        ticker_match = re.search(r'\(([A-Z0-9\-\.]+)\)', raw)
        ticker = ticker_match.group(1) if ticker_match else "N/A"

        company = re.split(r'\s+\(', raw)[0].strip()

        return company, ticker

    def _load_all_rows(self):
        """Load all json_processed files and flatten into a list of dicts.

        Each dict represents one context window hit and contains:
            company, ticker, cik, keyword, matched_phrase, context,
            hit_sentence_index, context_start_index, context_end_index
        """
        rows = []

        for json_file in sorted(self.json_processed_root.glob("*.json")):
            with open(json_file, "r", encoding="utf-8") as f:
                records = json.load(f)

            for record in records:
                metadata = record.get("metadata", {})
                filing = metadata.get("filing", {})
                keyword = metadata.get("keyword", "")
                context_windows = record.get("context", [])

                if not context_windows:
                    continue

                display_names = filing.get("display_names", [])
                company, ticker = self._parse_display_name(display_names)
                ciks = filing.get("ciks", [])
                cik = ciks[0] if ciks else ""

                for window in context_windows:
                    rows.append({
                        "company": company,
                        "ticker": ticker,
                        "cik": cik,
                        "keyword": keyword,
                        "matched_phrase": window.get("matched_phrase", ""),
                        "context": window.get("context", ""),
                        "hit_sentence_index": window.get("hit_sentence_index"),
                        "context_start_index": window.get("context_start_index"),
                        "context_end_index": window.get("context_end_index"),
                    })

        return rows

    def get_all_json_files(self):
        """Return a sorted list of all json_processed file paths."""
        return sorted(self.json_processed_root.glob("*.json"))

    def load_file(self, json_path):
        """Load and return the list of records from a single json_processed file."""
        with open(json_path, "r", encoding="utf-8") as f:
            return json.load(f)
