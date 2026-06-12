from typing_extensions import Self

from models.query_model import QueryModel

from nps_crawling.config import Config
from nps_crawling.crawler.utils import CrawlerPipeline
from nps_crawling.crawler.pre_fetch_utils.sec_params import (
    SecSearchParams,
    get_search_params_from_id
)

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

    def start_crawl(self) -> bool:
        model = QueryModel()
        parameters: list[str] = []

        for id in model.selected_queries:
            path: str = get_search_params_from_id(Config.GUI_QUERY_PATH, id=id)
            parameters.append(path)

        self.crawl.crawler_workflow(search_parameter_files=parameters)

        return True

    def stop_crawl(self) -> bool:
        from nps_crawling.utils.event_bus import bus
        bus.publish("crawler.stop")
        return False