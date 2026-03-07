"""Data processing for classification tasks using PyArrow datasets."""

import logging

import pyarrow.dataset as ds

from nps_crawling.config import Config

logger = logging.getLogger(__name__)

# Columns written by preprocessing (context windows): same shape as filter output
CONTEXT_COLUMNS = [
    "company",
    "ticker",
    "cik",
    "filing_url",
    "keywords_found",
    "matched_phrase",
    "context",
]


class ClassificationDataProcessing(Config):
    """Data processing class for classification tasks.

    Reads the context Parquet dataset (written by preprocessing), which is
    partitioned by company and has columns: company, ticker, cik, filing_url,
    keywords_found, matched_phrase, context (plus hit_sentence_index, etc.).
    """
    def __init__(self):
        """Initialize with the context Parquet dataset (lazy; tolerates missing/empty dir)."""
        self.parquet_root = Config.NPS_CONTEXT_PARQUET_PATH
        self._dataset = None
        self._ensure_dataset()

    def _ensure_dataset(self):
        """Create PyArrow dataset if the context root exists and contains Parquet data."""
        if not self.parquet_root.exists():
            logger.debug("Context parquet root does not exist: %s", self.parquet_root)
            return
        try:
            self._dataset = ds.dataset(
                self.parquet_root,
                format="parquet",
                partitioning="hive",
            )
        except Exception as e:
            logger.debug("Could not open context dataset: %s", e)
            self._dataset = None

    def get_list_of_all_companies(self):
        """Return unique sorted company names that have context windows."""
        if self._dataset is None:
            return []
        try:
            table = self._dataset.to_table(columns=["company"])
            companies = table["company"].to_pylist()
            return sorted({c for c in companies if c is not None and str(c).strip()})
        except Exception as e:
            logger.warning("Failed to list companies from context dataset: %s", e)
            return []

    def get_data_for_classification(self, company):
        """Return a DataFrame of context windows for the given company."""
        if self._dataset is None:
            import pandas as pd
            return pd.DataFrame(columns=CONTEXT_COLUMNS)
        try:
            table = self._dataset.to_table(
                columns=CONTEXT_COLUMNS,
                filter=ds.field("company") == company,
            )
            return table.to_pandas()
        except Exception as e:
            logger.warning("Failed to get data for company %r: %s", company, e)
            import pandas as pd
            return pd.DataFrame(columns=CONTEXT_COLUMNS)
