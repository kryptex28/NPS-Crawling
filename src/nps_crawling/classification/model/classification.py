"""Classification model pipeline."""

import json

from nps_crawling.config import Config
from nps_crawling.classification.model.model import get_classification_model


class ClassificationModelPipeline(Config):
    """Classification model pipeline class."""

    def __init__(self):
        """Initializes ClassificationModelPipeline."""
        super().__init__()

        print(f"Configured model: {self.MODEL}")
        self.llm = get_classification_model(self.MODEL)
        print(f"Loaded model class: {type(self.llm).__name__}")

    def model_workflow(self, records, source_filename):
        """Classify all context windows in the given records and save as JSON."""
        total_windows = sum(len(record.get("context", [])) for record in records)
        done = 0

        print(f"Starting file: {source_filename} ({total_windows} windows)")

        for record in records:
            for window in record.get("context", []):
                raw = self.llm.classify(window["context"])
                window["nps_classification"] = " | ".join(
                    line.strip() for line in raw.splitlines() if line.strip()
                )

                done += 1
                print(f"{source_filename}: {done}/{total_windows}")

        out_path = self.NPS_CLASSIFIED_JSON / f"{source_filename}.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(records, f, ensure_ascii=False, indent=2)

        print(f"Finished file: {source_filename}")