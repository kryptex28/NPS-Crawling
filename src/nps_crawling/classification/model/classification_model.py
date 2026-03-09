"""Classification model pipeline."""

import json

from nps_crawling.config import Config
from nps_crawling.llm.llm_ollama import LLMOllama


class ClassificationModelPipeline(Config):
    """Classification model pipeline class."""

    def __init__(
        self,
        model: str = "mistral",
        host: str = "localhost",
        port: int = 14000,
    ):
        """Initializes ClassificationModelPipeline."""
        super().__init__()

        self.llm = LLMOllama(
            persona=self.OLLAMA_PERSONA,
            model=model,
            host=host,
            port=port,
            temperature=0.0,
            top_p=1.0,
            top_k=1,
            num_predict=128,
            seed=42,
            repeat_penalty=1.0,
        )

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
