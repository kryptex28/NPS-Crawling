"""Storage pipeline to save processed context windows as JSON files."""

import json

from nps_crawling.config import Config
from nps_crawling.db.db_adapter import DbAdapter


class SaveToJSONPipeline(Config):
    """Storage pipeline to save processed records as JSON files."""
    def __init__(self):
        """Initialize the storage pipeline."""
        self.json_root = Config.NPS_CONTEXT_JSON_PATH / "files"
        self.json_reject_root = Config.NPS_REJECTED_JSON_PATH / "files"

        try:
            self.db = DbAdapter()
        except Exception:
            self.db = None

    def storage_workflow(self, records, source_filename, reject=False, update_db=True):
        """Write a list of processed records to a JSON file.

        Args:
            records: list of dicts, each containing "metadata", "core_text",
                     and "context" (list of context windows).
            source_filename: stem of the originating json_raw file, used as
                             the output filename.
            reject: if True, write to the json_reject directory instead.
            update_db: whether to update the database for the saved records.
        """
        target_dir = self.json_reject_root if reject else self.json_root
        out_path = target_dir / f"{source_filename}.json"

        # Filter out records that have no contexts left
        records_to_save = [r for r in records if len(r.get("context", [])) > 0]

        # Remove core_text from each record to save space in the final processed JSON
        for record in records_to_save:
            record.pop("core_text", None)

        # Save preprocessed json, only if there's anything to save
        if records_to_save:
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(records_to_save, f, ensure_ascii=False, indent=2)

        # Update the path in the database for each record saved in this batch
        if update_db and hasattr(self, 'db') and self.db is not None:
            # First map and deduplicate whether each filing_id has any context across this batch
            filing_relevances = {}
            for record in records:
                metadata = record.get("metadata", {})
                filing_id = None
                if "id" in metadata:
                    filing_id = metadata["id"]
                elif "filing" in metadata and isinstance(metadata["filing"], dict):
                    filing_id = metadata["filing"].get("id")

                if filing_id:
                    has_contexts = len(record.get("context", [])) > 0
                    if filing_id not in filing_relevances:
                        filing_relevances[filing_id] = has_contexts
                    else:
                        filing_relevances[filing_id] = filing_relevances[filing_id] or has_contexts

            # Now update the database for each unique filing_id
            for filing_id, is_relevant in filing_relevances.items():
                try:
                    if is_relevant:
                        self.db.update_path_to_preprocessed(filing_id, str(out_path.absolute()))
                    self.db.update_filing(filing_id, nps_relevant=is_relevant)
                except Exception:
                    pass

    def count_json_files(self):
        """Count processed JSON files."""
        return sum(1 for _ in self.json_root.glob("*.json"))

    def count_rejected_files(self):
        """Count rejected JSON files."""
        return sum(1 for _ in self.json_reject_root.glob("*.json"))
