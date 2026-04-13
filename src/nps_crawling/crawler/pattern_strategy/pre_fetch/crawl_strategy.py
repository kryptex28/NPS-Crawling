from nps_crawling.crawler.pattern_strategy.pre_fetch.fetch_strategy import FetchStrategy
from nps_crawling.utils.filings import Filing
from nps_crawling.crawler.spiders.link_spider import LinkSpider

from scrapy.crawler import CrawlerRunner
from scrapy.utils.project import get_project_settings
from twisted.internet import defer, reactor

import logging

logger = logging.getLogger(__name__)

class CrawlStrategy(FetchStrategy):
    

    def __init__(self) -> None:
        super().__init__()

    def fetch(self, query_path: str, **kwargs) -> list[Filing]:
        results: list[str] = []
        filings: list[Filing] = []

        runner: CrawlerRunner = CrawlerRunner(settings=get_project_settings())

        @defer.inlineCallbacks
        def crawl():
            yield runner.crawl(LinkSpider, url="", results=results)
            reactor.stop()

        crawl()
        reactor.run()

        for url in results:
            filings.append(Filing(url,
                                  "",
                                  ciks=[],
                                  ticker=[],
                                  period_ending="",
                                  file_num=[],
                                  display_names=[],
                                  xsl="",
                                  sequence="",
                                  root_forms=[],
                                  file_date="",
                                  biz_states=[],
                                  sics=[],
                                  form="",
                                  adsh="",
                                  film_num=[],
                                  biz_locations=[],
                                  file_type="",
                                  file_description="",
                                  inc_states=[],
                                  file_path_name="",
                                  keyword=""))

        return filings