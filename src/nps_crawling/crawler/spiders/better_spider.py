"""Improved Spider to crawl SEC filings for NPS mentions based on parameters and SEC search function."""
import io
import os
from typing import Any, AsyncIterator, Iterable, Self

import pypdf
import scrapy
from scrapy.crawler import Crawler
from scrapy.utils.project import get_project_settings
from scrapy import signals

from nps_crawling.crawler.items import FilingItem
from nps_crawling.utils.filings import Filing
from nps_crawling.utils.sec_params import create_params_from_config
from nps_crawling.utils.sec_query import SecParams, SecQuery


class BetterSpider(scrapy.Spider):
    """Improved Scrapy Spider for improved filing search (simply better)."""
    name = 'better_spider'

    def __init__(self,
                 callback=None,
                 queries: list[SecQuery] = None,
                 *args,
                 **kwargs):
        """Initializes spider."""
        super(BetterSpider, self).__init__()
        self.logger.info("Initializes spider.")
        # 'Hotkey' map for specific file types
        self.function_map: dict = {
            'pdf': self.extract_pdf_content,
            'xml': self.extract_xml_content,
            'html': self.extract_xml_content,
            'htm': self.extract_xml_content,
            'txt': self.extract_txt_content,
        }
        self.queries = queries
        self.callback = callback

    async def start(self) -> AsyncIterator[Any]:
        """Starts scrapy spider."""
        self.logger.info("Starting scrapy spider.")

        settings = get_project_settings()
        sec_query_limit_count: int = settings.get('SEC_QUERY_LIMIT_COUNT')
        query_file_path = settings.get('SEC_QUERY_FILE_PATH')

        # Create a list of parameters for all defined keywords in the config file
        sec_params: list[SecParams] = create_params_from_config(query_file_path)

        # Create a list of query to fetch all related documents
        sec_queries: list[SecQuery] = []
        for sec_param in sec_params:
            query: SecQuery = SecQuery(sec_params=sec_param, limit=sec_query_limit_count)
            sec_queries.append(query)

        # Fetch now all documents per query
        for sec_query in sec_queries:
            sec_query.fetch_filings()

        # Iterate through all filings
        for sec_query in sec_queries:
            for i, filing in enumerate(sec_query.keyword_filings):
                self.logger.info(f"Dispatching filing {filing.file_path_name} - Number: {i}.")
                url: str = filing.get_url()[0]
                yield scrapy.Request(
                    url=url,
                    callback=self.parse,
                    meta={'filing': filing,
                          'keyword': sec_query.sec_params.keyword,
                          },
                    dont_filter=True
                )

    def parse(self, response: scrapy.http.Response) -> Iterable[FilingItem]:
        """Parses filing and redirects to specific content extractor."""
        self.logger.info(f"Parsing {response.url}")
        filing: Filing = response.meta['filing']
        keyword: str = response.meta['keyword']

        # Extract text from response content
        text: str = self.function_map[filing.file_container_type](response)

        item: FilingItem = FilingItem()
        item['filing'] = filing
        item['core_text'] = text
        item['keyword'] = keyword

        # Dispatch into pipeline
        yield item

    def extract_txt_content(self, response: scrapy.http.Response) -> str:
        """Extracts content from TXT file."""
        self.logger.info(f"Extracting content from {response.url} as TXT.")
        return response.text

    def extract_pdf_content(self, response: scrapy.http.Response) -> str:
        """Extracts content from PDF file."""
        self.logger.info(f"Extracting content from {response.url} as PDF.")
        pdf_bytes: bytes = response.body
        reader: pypdf.PdfReader = pypdf.PdfReader(io.BytesIO(pdf_bytes))

        text_parts: list[str] = []

        for page in reader.pages:
            page_text: str = page.extract_text() or ''
            text_parts.append(page_text)

        core_text: str = '\n'.join(text_parts)
        return core_text

    def extract_xml_content(self, response: scrapy.http.Response) -> str:
        """Extracts content from HTML/XML file."""
        self.logger.info(f"Extracting content from {response.url} as XML/HTML.")
        return response.text

    def item_scraped(self, item: FilingItem, spider=None) -> None:
        """Called by Scrapy signal when an item is scraped."""
        if self.callback:
            # Extract the Filing object from the item
            filing = item.get('filing')
            if filing:
                self.callback(filing)

    @classmethod
    def from_crawler(cls, crawler: Crawler, *args, **kwargs):
        spider = super().from_crawler(crawler, *args, **kwargs)
        # Connect the spider.item_scraped method to the item_scraped signal
        crawler.signals.connect(spider.item_scraped, signal=signals.item_scraped)
        return spider