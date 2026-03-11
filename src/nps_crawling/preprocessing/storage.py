"""Storage pipeline to save processed context windows as JSON files."""

import json
from pathlib import Path

from nps_crawling.config import Config
from nps_crawling.db.db_adapter import DbAdapter


class SaveToJSONPipeline(Config):
    """Storage pipeline to save processed records as JSON files."""
    def __init__(self):
        """Initialize the storage pipeline."""
        self.json_root = Config.NPS_CONTEXT_JSON_PATH
        self.json_reject_root = Config.NPS_REJECTED_JSON_PATH

        try:
            self.db = DbAdapter()
        except Exception:
            self.db = None

    def storage_workflow(self, records, source_filename, reject=False):
        """Write a list of processed records to a JSON file.

        Args:
            records: list of dicts, each containing "metadata", "core_text",
                     and "context" (list of context windows).
            source_filename: stem of the originating json_raw file, used as
                             the output filename.
            reject: if True, write to the json_reject directory instead.
        """
        target_dir = self.json_reject_root if reject else self.json_root
        out_path = target_dir / f"{source_filename}.json"

        # Save preprocessed json
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(records, f, ensure_ascii=False, indent=2)

        # Update the path in the database for each record saved in this batch
        if hasattr(self, 'db') and self.db is not None:
            for record in records:
                # Based on docstring, record contains a "metadata" dictionary
                # which hopefully contains "filing" block or at least an "id".
                # For preprocessing, if "filing" sub-dict is missing, we try to fall back:
                metadata = record.get("metadata", {})
                filing_id = None

                # Check root metadata
                if "id" in metadata:
                    filing_id = metadata["id"]
                elif "filing" in metadata and isinstance(metadata["filing"], dict):
                    filing_id = metadata["filing"].get("id")

                # Update DB using explicit method
                if filing_id:
                    try:
                        self.db.update_path_to_preprocessed(filing_id, str(out_path.absolute()))
                    except Exception:
                        pass

    def count_json_files(self):
        """Count processed JSON files."""
        return sum(1 for _ in self.json_root.glob("*.json"))

    def count_rejected_files(self):
        """Count rejected JSON files."""
        return sum(1 for _ in self.json_reject_root.glob("*.json"))
