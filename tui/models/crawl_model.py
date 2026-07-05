from __future__ import annotations
import json
from pathlib import Path
from typing import Any
from typing_extensions import Self

from models.query_model import QueryModel

from nps_crawling.config import Config
from nps_crawling.crawler.pre_fetch_utils.sec_params import (
    get_search_params_from_id
)
from nps_crawling.db.db_adapter import DbAdapter
from nps_crawling.utils.project_manager import get_git_root
from nps_crawling.project_config import active_project_file


class CrawlModel():

    instance = None

    def __new__(cls) -> Self:
        """Create or return the singleton instance of CrawlModel."""
        if cls.instance is None:
            cls.instance = super().__new__(cls)
        return cls.instance

    def __init__(self) -> None:
        """Initialize the CrawlModel instance."""
        if not hasattr(self, "_initialized"):
            self._initialized = True
            self._crawl = None
            self.queries: list[str] = []

    @property
    def crawl(self) -> Any:
        """Lazy load and return the CrawlerPipeline instance."""
        if self._crawl is None:
            from nps_crawling.crawler.utils import CrawlerPipeline
            self._crawl = CrawlerPipeline()
        return self._crawl

    def start_crawl(self) -> bool:
        """Start the crawling process using the selected queries and limits."""
        Config.reload_config()
        DbAdapter().ensure_table_exists()
        model = QueryModel()
        parameters: list[str] = []

        for id in model.selected_queries:
            path: str = get_search_params_from_id(str(Config.QUERY_PATH), id=id)
            parameters.append(path)

        self.crawl.crawler_workflow(search_parameter_files=parameters,
                                    limit=Config.CRAWL_SEC_QUERY_LIMIT_COUNT)

        return True

    def stop_crawl(self) -> bool:
        """Publish a stop signal to the event bus to halt the crawl pipeline."""
        from nps_crawling.utils.event_bus import bus
        bus.publish("crawler.stop")
        return False

    def get_config_path(self) -> Path:
        """Retrieve the path to the crawl configuration file."""
        root = get_git_root()
        try:
            proj_file = active_project_file(root)
            if proj_file and proj_file.is_file():
                with open(proj_file, "r", encoding="utf-8") as f:
                    proj_data = json.load(f)
                crawl_ref = proj_data.get("crawl")
                from nps_crawling.project_config import section_config_path
                return section_config_path(crawl_ref, "crawl", root)
        except Exception:
            pass
        from nps_crawling.project_config import CONFIG_TREE_PATHS
        return root / CONFIG_TREE_PATHS["crawl"]

    def get_config(self) -> dict[str, Any]:
        """Load and return the crawl configuration dictionary."""
        path = self.get_config_path()
        if path.is_file():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def save_config(self, updates: dict[str, Any]) -> None:
        """Save updates to the crawl configuration file."""
        root = get_git_root()
        from nps_crawling.project_config import save_project_section
        try:
            save_project_section("crawl", updates, root)
        except Exception:
            # Fallback if no active project is loaded
            path = self.get_config_path()
            config_data = self.get_config()
            config_data.update(updates)
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)

        Config.reload_config()