"""Utility functions for the NPS Crawling spider."""
from scrapy.utils.reactor import install_reactor
install_reactor('twisted.internet.asyncioreactor.AsyncioSelectorReactor')

import logging
import os

from scrapy.crawler import CrawlerProcess
from scrapy.crawler import CrawlerRunner
from scrapy.utils.project import get_project_settings
from twisted.internet import defer, reactor

from nps_crawling.config import Config
from nps_crawling.crawler.spiders.better_spider import BetterSpider
from nps_crawling.utils.filings import Filing
from nps_crawling.utils.sec_params import SecSearchParams, create_search_params_from_config
from nps_crawling.utils.sec_query import SecQuery

logger = logging.getLogger(__name__)


class CrawlerPipeline(Config):
    """Crawler pipeline to run the NPS Crawling spider."""
    def __init__(self):
        """Initialize the CrawlerPipeline."""
        pass

    def prefetch_data(self, query_path: str) -> list[Filing]:
        # Create search parameters based on queries
        search_parameters: list[SecSearchParams] = create_search_params_from_config(query_path)

        # Create queries
        sec_queries: list[SecQuery] = []
        for parameter in search_parameters:
            query: SecQuery = SecQuery(sec_params=parameter)
            sec_queries.append(query)

        # Fetch all filings per query
        filings_dict: dict[str, Filing] = {}
        duplicates: dict[str, list[Filing]] = {}

        for query in sec_queries:
            temp: list[Filing] = query.fetch_filings()
            print(len(temp))
            for filing in temp:
                if filing.id in filings_dict:
                    # Collect duplicates for analysis
                    if filing.id not in duplicates:
                        duplicates[filing.id] = [filings_dict[filing.id]]
                    duplicates[filing.id].append(filing)
                else:
                    filings_dict[filing.id] = filing

        filings = list(filings_dict.values())

        for _id, dupes in duplicates.items():
            logger.info(f"Found for ID {_id} {len(dupes)} duplicates.")
            
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

        query_files = [
            os.path.join(SEC_QUERY_DIR_PATH, f)
            for f in os.listdir(SEC_QUERY_DIR_PATH)
            if os.path.isfile(os.path.join(SEC_QUERY_DIR_PATH, f))
        ]

        runner = CrawlerRunner(settings=settings)

        @defer.inlineCallbacks
        def crawl_sequentially():
            try:
                for query_file in query_files:
                    filings = self.prefetch_data(query_path=query_file)
                    logger.info(f"Running spider for {query_file} with {len(filings)} filings")
                    yield runner.crawl(BetterSpider, filings=filings)
                    logger.info(f"Finished: {query_file}")
            except Exception as e:
                logger.error(f"Crawl error: {e}", exc_info=True)
            finally:
                reactor.stop()  # type: ignore[attr-defined]

        crawl_sequentially()
        reactor.run()

        # Run spider
        #process = CrawlerProcess(settings)

        #process.crawl(BetterSpider,
         #             filings=filings)
        #process.start()

        return None
