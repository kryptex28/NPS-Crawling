from abc import ABC, abstractmethod
from nps_crawling.crawler.pre_fetch_utils.filings import Filing

class FetchStrategy(ABC):

    @abstractmethod
    def fetch(self, query_path: str, **kwargs) -> list[Filing]:
        pass