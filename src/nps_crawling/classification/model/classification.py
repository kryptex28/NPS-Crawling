"""Classification model pipeline."""

import json

from nps_crawling.classification.model.model import get_classification_model
from nps_crawling.config import Config


class ClassificationModelPipeline(Config):
    """Classification model pipeline class."""

    def __init__(
        self,
    ):
        """Initializes ClassificationModelPipeline."""
        super().__init__()

        self.llm = get_classification_model(self.MODEL)

    def model_workflow(self, records, source_filename):
        """Classify all context windows in the given records and save as JSON.

        For each record, each context window in "context" is classified by the
        LLM and a "nps_classification" field is added to the window dict.
        The enriched records are written to json_classified/<source_filename>.json.

        Args:
            records: list of dicts loaded from a json_processed file.
            source_filename: stem of the source file, used as output filename.
        """
        for record in records:
            for window in record.get("context", []):
                raw = self.llm.classify(window["context"])
                window["nps_classification"] = " | ".join(line.strip() for line in raw.splitlines() if line.strip())

        out_path = self.NPS_CLASSIFIED_JSON / f"{source_filename}.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(records, f, ensure_ascii=False, indent=2)
