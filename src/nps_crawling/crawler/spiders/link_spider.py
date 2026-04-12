from urllib.parse import urlparse

import scrapy


class LinkSpider(scrapy.Spider):
    name: str = "link_spider"

    def __init__(self, url: str, results: list[str], *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.start_urls: list[str] = [url]
        self.results: list[str] = results  # reference to external list
        self.seen: set[str] = set()        # instance-level deduplication

    def parse(self, response: scrapy.http.Response) -> None:
        for href in response.css("a::attr(href)").getall():
            absolute = response.urljoin(href)
            parsed = urlparse(absolute)
            if parsed.scheme not in ("http", "https"):
                continue
            if absolute not in self.seen:
                self.seen.add(absolute)
                self.results.append(absolute)
