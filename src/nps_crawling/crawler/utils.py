"""Utility functions for the NPS Crawling spider."""
from scrapy.utils.reactor import install_reactor

install_reactor('twisted.internet.asyncioreactor.AsyncioSelectorReactor')

import logging
import os
import crochet
from scrapy.crawler import CrawlerRunner
from scrapy.utils.project import get_project_settings
from twisted.internet import defer, reactor

from nps_crawling.config import Config
from nps_crawling.crawler.spiders.better_spider import BetterSpider

from nps_crawling.crawler.pattern_strategy.pre_fetch.fetch_strategy import FetchStrategy
from nps_crawling.crawler.pattern_strategy.pre_fetch.crawl_strategy import CrawlStrategy
from nps_crawling.crawler.pattern_strategy.pre_fetch.search_strategy import SearchStrategy

logger = logging.getLogger(__name__)
crochet.setup()

@crochet.wait_for(timeout=3600)
@defer.inlineCallbacks
def _run_crawl_sequentially(runner: CrawlerRunner,
                            query_files: list[str],
                            fetch_strategy: FetchStrategy,
                            ignore_lookup: bool):
    try:
        for query_file in query_files:
            filings = fetch_strategy.fetch(query_path=query_file, ignore_lookup=ignore_lookup)
            logger.info(f"Running spider for {query_file} with {len(filings)} filings")
            yield runner.crawl(BetterSpider, filings=filings)
            logger.info(f"Finished: {query_file}")
    except Exception as e:
        logger.error(f"Crawl error: {e}", exc_info=True)
    finally:
        reactor.stop()  # type: ignore[attr-defined]

class CrawlerPipeline(Config):
    """Crawler pipeline to run the NPS Crawling spider."""
    def __init__(self):
        """Initialize the CrawlerPipeline."""
        pass

    def crawler_workflow(self,
                         dry_run: bool = False,
                         db_only: bool = False,
                         prefetch_only: bool = False,
                         ignore_lookup: bool = False,
                         limit: int = -1) -> None:
        """Run the NPS Crawling spider with specified settings."""
        os.environ['SCRAPY_SETTINGS_MODULE'] = 'nps_crawling.crawler.settings'

        settings = get_project_settings()
        settings.update({'CRAWL_DRY_RUN': dry_run})
        settings.update({'CRAWL_DB_ONLY': db_only})
        settings.update({'CRAWL_IGNORE_LOOKUP': ignore_lookup})
        if settings.get("SEC_QUERY_LIMIT_COUNT", None) is not None:
            settings.update({'SEC_QUERY_LIMIT_COUNT': limit})

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

        if prefetch_only:
            total_size: int = 0
            for query_file in query_files:
                filings = fetch_strategy.fetch(query_path=query_file, ignore_lookup=ignore_lookup)
                for filing in filings:
                    logger.info(filing)
                total_size += len(filings)

            logger.info(f"Total crawled filings from {len(query_files)} queries: {total_size}")

        else:
            runner = CrawlerRunner(settings=settings)

        _run_crawl_sequentially(runner=runner, query_files=query_files, fetch_strategy=fetch_strategy, ignore_lookup=ignore_lookup)

        return None
