"""Classification model pipeline."""

import json
import hashlib

from nps_crawling.db.db_adapter import DbAdapter
from nps_crawling.classification.model import get_model_class, ModelBase
from nps_crawling.classification.options import get_classification_option, ClassificationOptionName
from nps_crawling.config import Config
import logging

logger = logging.getLogger(__name__)


class ClassificationModelPipeline(Config):
    """Classification model pipeline class."""

    def __init__(self):
        """Initializes ClassificationModelPipeline."""
        super().__init__()

        self.classification_models : dict[ClassificationOptionName, ModelBase] = {}

        for classification_option in self.CLASSIFICATION_CONFIG:
            logger.info(f"Loading Model for: {classification_option}")
            self.classification_models[classification_option] = get_model_class(
                self.CLASSIFICATION_CONFIG[classification_option]["model_class"],
                self.CLASSIFICATION_CONFIG[classification_option].get("model_params", {}),
            )

        self.adapter = DbAdapter()

        with open(self.NPS_CLASSIFIED_JSON / "files" / "config.json", "w", encoding="utf-8") as f:
            json.dump(self.CLASSIFICATION_CONFIG, f, ensure_ascii=False, indent=2)

    def _write_to_db(self, record):
        payload = json.dumps(self.config, sort_keys=True, separators=(",", ":"))
        experiment_version = hashlib.md5(payload.encode()).hexdigest()
        self.adapter.upsert_classification(
            # --- Pflicht- und Metadaten-Felder ---
            filing_id="0001234567-24-000001",                 # ID des Filings
            version=experiment_version,                          # Deine aktuelle Experiment-Version
            path_to_classified = str(self.NPS_CLASSIFIED_JSON / "files"),    # Pfad für die Haupttabelle (neu!)
            # --- Hauptkategorien (Boolesche Flags) ---
            KPI_CURRENT_VALUE=True,
            KPI_TREND=False,
            KPI_HISTORICAL_COMPARISON=True,
            BENCHMARK_COMPARISON_POSITIVE=False,
            BENCHMARK_COMPARISON_NEGATIVE=False,
            NPS_GOAL_REACHED=True,
            TARGET_OUTLOOK=False,
            MGMT_COMPENSATION_GOVERNANCE=False,
            CUSTOMER_CASE_EVIDENCE=True,
            NPS_SERVICE_PROVIDER=False,
            METHODOLOGY_DEFINITION=True,
            QUALITATIVE_ONLY=False,
            OTHER=False,
            # --- Kategorie Helper / Extrahierte Zusatzdaten ---
            has_numeric_nps=True,            # Boolean (Ist eine konkrete Zahl extrahiert worden?)
            
            # --- Numerische Float-Werte (falls vorhanden, ansonsten None) ---
            nps_value_fix=12.5,              # Direkter NPS Wert (z.B. 12.5)
            nps_competition_industry=None,   # NPS der Industrie/Konkurrenz
            nps_value_over=15.0,             # Wenn z.B. gesagt wird "NPS over 15"
            nps_value_below=None,            # Wenn z.B. gesagt wird "NPS below 10"
            nps_goal_value=20.0,             # Zielwert für den NPS
            nps_goal_change=2.5              # Angestrebte Veränderung des NPS
        )

    def model_workflow(self, records, source_filename):
        """Classify all context windows in the given records and save as JSON."""
        total_windows = sum(len(record.get("context", [])) for record in records)
        done = 0

        logger.info(f"Starting file: {source_filename} ({total_windows} windows)")

        for record in records:
            for window in record.get("context", []):
                for classification_option in self.CLASSIFICATION_CONFIG:
                    model = self.classification_models[classification_option]
                    option = get_classification_option(classification_option)
                    results = model.classify(option, window["context"])
                    for result in results:
                        window[result.column_name] = result.entry
                    
                done += 1
                logger.info(f"{source_filename}: {done}/{total_windows}")

        out_path = self.NPS_CLASSIFIED_JSON / "files" / f"{source_filename}.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(records, f, ensure_ascii=False, indent=2)

        logger.info(f"Finished file: {source_filename}")
