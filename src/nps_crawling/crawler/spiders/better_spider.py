"""Improved Spider to crawl SEC filings for NPS mentions based on parameters and SEC search function."""
import io
from typing import Any, AsyncIterator, Iterable

import pypdf
import scrapy
from scrapy.utils.project import get_project_settings

from nps_crawling.crawler.items import FilingItem
from nps_crawling.db.db_adapter import DbAdapter
from nps_crawling.utils.filings import Filing
from nps_crawling.utils.sec_params import create_search_params_from_config
from nps_crawling.utils.sec_query import SecQuery, SecSearchParams


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

        # 'Hotkey' map for specific file types
        self.function_map: dict = {
            'pdf': self.extract_pdf_content,
            'xml': self.extract_xml_content,
            'html': self.extract_xml_content,
            'htm': self.extract_xml_content,
            'txt': self.extract_txt_content,
        }

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
        text: str = self.function_map[filing.file_container_type](response)

        item: FilingItem = FilingItem()
        item['filing'] = filing
        item['core_text'] = text
        item['keyword'] = keyword
        item['url'] = url

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
