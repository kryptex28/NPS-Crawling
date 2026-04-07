"""Utility functions for the NPS Crawling spider."""

import logging
import os

from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings

from nps_crawling.config import Config
from nps_crawling.crawler.spiders.better_spider import BetterSpider
from nps_crawling.utils.filings import Filing
from nps_crawling.utils.sec_params import SecSearchParams, create_search_params_from_config_dir
from nps_crawling.utils.sec_query import SecQuery

logger = logging.getLogger(__name__)


class CrawlerPipeline(Config):
    """Crawler pipeline to run the NPS Crawling spider."""
    def __init__(self):
        """Initialize the CrawlerPipeline."""
        pass

    def prefetch_data(self, query_path: str) -> list[Filing]:
        # Create search parameters based on queries
        search_parameters: list[SecSearchParams] = create_search_params_from_config_dir(query_path)

        # Create queries
        sec_queries: list[SecQuery] = []
        for parameter in search_parameters:
            query: SecQuery = SecQuery(sec_params=parameter)
            sec_queries.append(query)

        # Fetch all filings per query
        filings: list[Filing] = []
        for query in sec_queries:
            temp: list[Filing] = query.fetch_filings()
            print(len(temp))
            filings.extend(temp)

        return filings

    def crawler_workflow(self):
        """Run the NPS Crawling spider with specified settings."""
        os.environ['SCRAPY_SETTINGS_MODULE'] = 'nps_crawling.crawler.settings'

        settings = get_project_settings()

        settings.update({'LOG_LEVEL': logger.getEffectiveLevel()})

        print("=== Active Scrapy Settings ===")
        for name, value in settings.items():
            print(f"{name}: {value}")
        print("=== End of Settings ===\n")

        # TODO: Abstract logic
        PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        SEC_QUERY_DIR_PATH = os.path.join(PROJECT_ROOT, 'queries')
        filings: list[Filing] = self.prefetch_data(query_path=SEC_QUERY_DIR_PATH)

        # Run spider
        process = CrawlerProcess(settings)

        process.crawl(BetterSpider,
                      filings=filings)
        process.start()

        return None
