"""Pipelines for storing crawled data."""
import json
from datetime import datetime
from uuid import uuid4

from nps_crawling.config import Config
from nps_crawling.db.db_adapter import DbAdapter


class SaveToJSONPipeline(Config):
    """Collect scraped items during a crawl and persist them as JSON files.

    Each record is written as a JSON file with two top-level keys:
    - ``metadata``: all filing fields except ``core_text``
    - ``core_text``: the extracted text content of the filing
    """

    def __init__(self):
        """Initialize pipeline state."""
        self.json_root = Config.RAW_JSON_PATH_CRAWLER
        self.records = []
        self.flush_every = 1

        # Initialize the database adapter for real-time upserts
        try:
            self.db = DbAdapter()
        except ModuleNotFoundError as e:
            # For environments where SQLAlchemy or psycopg2 isn't strictly required
            pass
        except ValueError as e:
            # Fallback if connection string provides errors
            self.db = None

    def open_spider(self, spider):
        """Reset the in-memory buffer when the spider starts."""
        self.records = []

    def _to_serializable(self, val):
        """Recursively convert a value to a JSON-serializable type."""
        if isinstance(val, (str, int, float, bool, type(None))):
            return val
        if isinstance(val, list):
            return [self._to_serializable(x) for x in val]
        if hasattr(val, "__dict__"):
            return {
                k: self._to_serializable(v)
                for k, v in vars(val).items()
                if not k.startswith("_")
            }
        return str(val)

    def process_item(self, item, spider):
        """Buffer a single scraped item, store in DB immediately, and flush buffer when full."""
        record = dict(item)

        url = self._to_serializable(record.pop("url"))
        core_text = self._to_serializable(record.pop("core_text", None))
        metadata = {k: self._to_serializable(v) for k, v in record.items()}

        # 1. Add to Postgres right away
        if hasattr(self, 'db') and self.db is not None:
            # Reconstruct the filing dictionary since scrapy items are flat
            filing = metadata.get("filing", {})
            keyword = metadata.get("keyword")
            filing_id = filing.get("id")

            if filing_id:
                if self.db.filing_exists(filing_id):
                    if keyword:
                        self.db.add_keyword(filing_id, keyword)
                else:
                    keywords_list = [keyword] if keyword else []
                    # path_to_raw will be set later during the flush, so we set it to None initially

                    try:
                        self.db.add_filing(
                            filing_id=filing_id,
                            ciks=filing.get("ciks", []),
                            period_ending=filing.get("period_ending"),
                            display_names=filing.get("display_names", []),
                            root_forms=filing.get("root_forms", []),
                            file_date=filing.get("file_date"),
                            form=filing.get("form"),
                            adsh=filing.get("adsh"),
                            file_type=filing.get("file_type"),
                            file_description=filing.get("file_description"),
                            film_num=filing.get("film_num", []),
                            keywords=keywords_list,
                            blacklisted=False,
                            nps_relevant=False,
                            path_to_raw=None,  # Will be set once batched to disk

                            # New NPS fields
                            nps_competition_industry=False,
                            nps_value_over=None,
                            nps_value_below=None,
                            nps_goal_value=None,
                            nps_goal_reached=False,
                            KPI_CURRENT_VALUE=None,
                            KPI_HISTORICAL_COMPARISON=False,
                            BENCHMARK_COMPARISON=False,
                            CUSTOMER_CASE_EVIDENCE=False,
                            METHODOLOGY_DEFINITION=False,
                            MGMT_COMPENSATION_GOVERNANCE=False,
                            QUALITATIVE_ONLY=False,
                            TARGET_OUTLOOK=False,
                            NPS_SERVICE_PROVIDER=False,
                            OTHER=False,
                            has_numeric_nps=False,
                            nps_value_fix=None,
                            nps_trend_sentiment=None,
                            nps_scope=None,
                            nps_formal_role=None,
                        )
                    except Exception as e:
                        # Log silently or configure scrapy logger and skip
                        pass

        # 2. Add to Memory buffer for JSON export
        self.records.append({"metadata": metadata, "core_text": core_text, "url": url})

        if len(self.records) >= self.flush_every:
            self._flush_buffer()
        return item

    def close_spider(self, spider):
        """Flush any remaining records when the spider closes."""
        if self.records:
            self._flush_buffer()

    def _flush_buffer(self):
        if not self.records:
            return

        ts = datetime.utcnow().strftime("%Y%m%dT%H%M%S")
        fname = f"chunk_{ts}_{uuid4().hex}.json"

        # Save raw json to file
        saved_path = self.json_root / fname
        with open(saved_path, "w", encoding="utf-8") as f:
            json.dump(self.records, f, ensure_ascii=False, indent=2)

        # Update the path_to_raw in the database since the file is now saved
        if hasattr(self, 'db') and self.db is not None:
            for record in self.records:
                metadata = record.get("metadata", {})
                filing = metadata.get("filing", {})
                filing_id = filing.get("id")

                if filing_id:
                    try:
                        self.db.update_path_to_raw(filing_id, str(saved_path.absolute()))
                    except Exception:
                        pass

        self.records = []
