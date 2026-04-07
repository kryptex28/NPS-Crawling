"""Improved Spider to crawl SEC filings for NPS mentions based on parameters and SEC search function."""
import io
import httpx
from typing import Any, AsyncIterator, Iterable

import pypdf
import scrapy
from scrapy.utils.project import get_project_settings

from nps_crawling.crawler.items import FilingItem
from nps_crawling.db.db_adapter import DbAdapter
from nps_crawling.utils.filings import Filing
from nps_crawling.utils.sec_params import create_search_params_from_config
from nps_crawling.utils.sec_query import SecQuery, SecSearchParams

from nps_crawling.utils.image_extraction.image_extractor_strategy import ImageExtractorStrategy
from nps_crawling.utils.image_extraction.easyocr_ocr_strategy import EasyOCRStrategy

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

        self.image_extractor: ImageExtractorStrategy = EasyOCRStrategy()

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

        image_text: str = self._extract_embedded_image_text(response, filing.file_container_type)

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

    def extract_image_content(self, response: scrapy.http.Response) -> str:
        self.logger.info(f"Extracting content from {response.url} as image.")
        result = self.image_extractor.extract(response.body)
        self.logger.debug(f"Image confidence: {result['metadata'].get('avg_confidence')}")
        return result["text"]
    
    def _extract_embedded_image_text(self, response: scrapy.http.Response, file_type: str) -> str:
        parts: list[str] = []

        if file_type in ('html', 'htm', 'xml'):
            for img_url in response.css("img::attr(src)").getall():
                abs_url: str = response.urljoin(img_url)
                try:
                    headers = {
                        "User-Agent": "your-app-name contact@youremail.com"
                    }

                    img_response = httpx.get(abs_url,
                                             headers=headers,
                                             follow_redirects=True, 
                                             timeout=10)
                    img_response.raise_for_status()
                    result = self.image_extractor.extract(img_response.content)

                    if result["text"].strip():
                        parts.append(f"[{abs_url}]: {result['text'].strip()}")
                except Exception as e:
                    self.logger.warning(f"Failed to extract image {abs_url}: {e}")
        elif file_type == 'pdf':
            reader = pypdf.PdfReader(io.BytesIO(response.body))
            for page_num, page in enumerate(reader.pages):
                for img_num, image_obj in enumerate(page.images):
                    try:
                        result = self.image_extractor.extract(image_obj.data)
                        if result["text"].strip():
                            parts.append(
                                f"[page {page_num + 1}, img {img_num + 1}]: {result['text'].strip()}"
                            )
                    except Exception as e:
                        self.logger.warning(f"Failed PDF image p{page_num + 1}/i{img_num + 1}: {e}")
        return "\n".join(parts)