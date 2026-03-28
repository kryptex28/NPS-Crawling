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
        self.json_root = Config.RAW_JSON_PATH_CRAWLER / "files"
        self.records = []
        self.flush_every = 1

        self.stats = {
            "total_items_crawled": 0,
            "new_records_added_to_db": 0,
            "existing_records_updated": 0,
            "keywords_found": set(),
        }

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
        self.start_timestamp = datetime.now()

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
                self.stats["total_items_crawled"] += 1
                if keyword:
                    self.stats["keywords_found"].add(keyword)

                if self.db.filing_exists(filing_id):
                    self.stats["existing_records_updated"] += 1
                    if keyword:
                        self.db.add_keyword(filing_id, keyword)
                else:
                    self.stats["new_records_added_to_db"] += 1
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
                            nps_relevant=None,
                            path_to_raw=None,  # Will be set once batched to disk
                            url=url,

                            # Main Categories
                            KPI_CURRENT_VALUE=None,
                            KPI_TREND=None,
                            KPI_HISTORICAL_COMPARISON=None,
                            BENCHMARK_COMPARISON=None,
                            TARGET_OUTLOOK=None,
                            MGMT_COMPENSATION_GOVERNANCE=None,
                            CUSTOMER_CASE_EVIDENCE=None,
                            NPS_SERVICE_PROVIDER=None,
                            METHODOLOGY_DEFINITION=None,
                            QUALITATIVE_ONLY=None,
                            OTHER=None,
                            # Category Helper Columns
                            has_numeric_nps=None,
                            numeric_nps_count=None,
                            nps_value_fix=None,
                            nps_competition_industry=None,
                            nps_value_over=None,
                            nps_value_below=None,
                            nps_goal_value=None,
                            nps_goal_change=None,
                            nps_goal_reached=None,
                            nps_trend_detected=None,
                            has_target_language=None,
                            keywords_found=None,
                            matched_phrase=None,
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

        end_timestamp = datetime.now()
        duration = end_timestamp - getattr(self, "start_timestamp", end_timestamp)
        tot_sec = int(duration.total_seconds())
        hrs, rem = divmod(tot_sec, 3600)
        mins, secs = divmod(rem, 60)
        fmt_duration = f"{hrs:02d}h {mins:02d}m {secs:02d}s"

        # Generate and save crawl report
        report_dir = Config.RAW_JSON_PATH_CRAWLER / "crawl_reports"
        report_dir.mkdir(parents=True, exist_ok=True)

        ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        report_path = report_dir / f"crawl_report_{ts}.json"

        # Read query.json content
        query_json_path = Config.ROOT_DIR / "src" / "nps_crawling" / "queries" / "query.json"
        query_content = {}
        if query_json_path.exists():
            try:
                with open(query_json_path, "r", encoding="utf-8") as qf:
                    query_content = json.load(qf)
            except Exception as e:
                pass

        import nps_crawling.crawler.settings as crawler_settings
        custom_settings = {
            k: getattr(crawler_settings, k)
            for k in dir(crawler_settings)
            if k.isupper()
        }

        report_data = {
            "query": query_content,
            "crawler_settings": self._to_serializable(custom_settings),
            "statistics": {
                "total_items_crawled": self.stats["total_items_crawled"],
                "new_records_added_to_db": self.stats["new_records_added_to_db"],
                "existing_records_updated": self.stats["existing_records_updated"],
                "unique_keywords_found": list(self.stats["keywords_found"]),
                "crawl_duration": fmt_duration,
            },
        }

        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report_data, f, indent=4, ensure_ascii=False)

    def _flush_buffer(self):
        if not self.records:
            return

        ts = datetime.utcnow().strftime("%Y%m%dT%H%M%S")

        # Extract filing_id from the single record (flush_every = 1)
        filing_id = (
            self.records[0]
            .get("metadata", {})
            .get("filing", {})
            .get("id", uuid4().hex)  # fallback if missing
        )
        fname = f"{filing_id}.json"

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
                        print(f"{filing_id} updated")
                    except Exception:
                        pass

        self.records = []
