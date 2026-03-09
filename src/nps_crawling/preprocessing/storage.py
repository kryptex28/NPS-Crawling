"""Storage pipeline to save processed context windows as JSON files."""

import json
from pathlib import Path

from nps_crawling.config import Config


class SaveToJSONPipeline(Config):
    """Storage pipeline to save processed records as JSON files."""
    def __init__(self):
        """Initialize the storage pipeline."""
        self.json_root = Config.NPS_CONTEXT_JSON_PATH

    def storage_workflow(self, records, source_filename):
        """Write a list of processed records to a JSON file.

        Args:
            records: list of dicts, each containing "metadata", "core_text",
                     and "context" (list of context windows).
            source_filename: stem of the originating json_raw file, used as
                             the output filename.
        """
        out_path = self.json_root / f"{source_filename}.json"

        #TODO: David - preprocessed json saving
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(records, f, ensure_ascii=False, indent=2)

    def count_json_files(self):
        """For logging only."""
        return sum(1 for f in self.json_root.glob("*.json"))
