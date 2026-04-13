"""Utility functions for the NPS Crawling spider."""
from scrapy.utils.reactor import install_reactor

install_reactor('twisted.internet.asyncioreactor.AsyncioSelectorReactor')

import logging
import os

from scrapy.crawler import CrawlerProcess, CrawlerRunner
from scrapy.utils.project import get_project_settings
from twisted.internet import defer, reactor

from nps_crawling.config import Config
from nps_crawling.crawler.spiders.better_spider import BetterSpider
from nps_crawling.crawler.pre_fetch_utils.filings import Filing

from nps_crawling.crawler.pattern_strategy.pre_fetch.fetch_strategy import FetchStrategy
from nps_crawling.crawler.pattern_strategy.pre_fetch.crawl_strategy import CrawlStrategy
from nps_crawling.crawler.pattern_strategy.pre_fetch.search_strategy import SearchStrategy

logger = logging.getLogger(__name__)


class CrawlerPipeline(Config):
    """Crawler pipeline to run the NPS Crawling spider."""
    def __init__(self):
        """Initialize the CrawlerPipeline."""
        pass

    def crawler_workflow(self,
                         dry_run: bool = False):
        """Run the NPS Crawling spider with specified settings."""
        os.environ['SCRAPY_SETTINGS_MODULE'] = 'nps_crawling.crawler.settings'

        settings = get_project_settings()

        settings.update({'LOG_LEVEL': logger.getEffectiveLevel()})

        print("=== Active Scrapy Settings ===")
        for name, value in settings.items():
            print(f"{name}: {value}")
        print("=== End of Settings ===\n")

        SEC_QUERY_DIR_PATH = Config.QUERY_PATH
        fetch_strategy: FetchStrategy = SearchStrategy()

        query_files = [
            os.path.join(SEC_QUERY_DIR_PATH, f)
            for f in os.listdir(SEC_QUERY_DIR_PATH)
            if os.path.isfile(os.path.join(SEC_QUERY_DIR_PATH, f))
        ]

        if dry_run:
            total_size: int = 0
            for query_file in query_files:
                filings = fetch_strategy.fetch(query_path=query_file, ignore_lookup=True)
                for filing in filings:
                    logger.info(filing)
                total_size += len(filings)

            logger.info(f"Total crawled filings from {len(query_files)} queries: {total_size}")

        else:
            runner = CrawlerRunner(settings=settings)

            @defer.inlineCallbacks
            def crawl_sequentially():
                try:
                    for query_file in query_files:
                        filings = fetch_strategy.fetch(query_path=query_file)
                        logger.info(f"Running spider for {query_file} with {len(filings)} filings")
                        yield runner.crawl(BetterSpider, filings=filings)
                        logger.info(f"Finished: {query_file}")
                except Exception as e:
                    logger.error(f"Crawl error: {e}", exc_info=True)
                finally:
                    reactor.stop()  # type: ignore[attr-defined]

            crawl_sequentially()
            reactor.run()

        return None
