"""Improved Spider to crawl SEC filings for NPS mentions based on parameters and SEC search function."""
from typing import Any, AsyncIterator, Iterable

import scrapy

from nps_crawling.crawler.pattern_factory.processing_factory import ProcessingFactory
from nps_crawling.crawler.items import FilingItem
from nps_crawling.utils.filings import Filing


class BetterSpider(scrapy.Spider):
    """Improved Scrapy Spider for improved filing search (simply better)."""
    name = 'better_spider'

    def __init__(self,
                 filings: list[Filing] = [],
                 *args,
                 **kwargs):
        """Initializes spider."""

        super().__init__(*args, **kwargs)

        self.logger.info("Initializes spider.")

        self.filings: list[Filing] = filings


    async def start(self) -> AsyncIterator[Any]:
        """Starts scrapy spider."""
        self.logger.info("Starting scrapy spider.")

        for i, filing in enumerate(self.filings):
            self.logger.info(f"Dispatching filing {filing.file_path_name} - Number: {i}.")
            url: str = filing.get_url()[0]
            yield scrapy.Request(
                url=url,
                callback=self.parse,
                meta={'filing': filing,
                      'url': url,
                      },
                dont_filter=True,
            )

    def parse(self, response: scrapy.http.Response) -> Iterable[FilingItem]:
        """Parses filing and redirects to specific content extractor."""
        self.logger.info(f"Parsing {response.url}")
        filing: Filing = response.meta['filing']
        keyword: str = filing.keyword
        url: str = response.meta['url']

        # Extract text from response content
        try:
            text: str = ProcessingFactory.create(filing.file_container_type).extract(response=response)
        except ValueError as e:
            self.logger.exception(e, exc_info=True)
        except Exception as e:
            self.logger.exception(e, exc_info=True)

        item: FilingItem = FilingItem()
        item['filing'] = filing
        item['core_text'] = text
        item['keyword'] = keyword
        item['url'] = url

        # Dispatch into pipeline
        yield item