from typing_extensions import Self

from nps_crawling.crawler.utils import CrawlerPipeline

class CrawlModel():

    instance = None

    def __new__(cls) -> Self:
        if cls.instance is None:
            cls.instance = super().__new__(cls)
        return cls.instance

    def __init__(self) -> None:
        self._crawl: CrawlerPipeline | None = None

        self.queries: list[str] = []

    @property
    def crawl(self) -> CrawlerPipeline:
        if self._crawl is None:
            self._crawl = CrawlerPipeline()
        return self._crawl

    def start_crawl(self, ids: list) -> bool:
        self.crawl.crawler_workflow(search_parameter_files=ids)

        return True

    def stop_crawl(self) -> bool:
        from nps_crawling.utils.event_bus import bus
        bus.publish("crawler.stop")