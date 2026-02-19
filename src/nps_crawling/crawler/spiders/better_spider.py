import io
from typing import Iterable, Any, AsyncIterator

import scrapy
import pypdf

from nps_crawling.crawler.items import FilingItem
from nps_crawling.utils.sec_query import SecQuery
from nps_crawling.utils.filings import Filing, FilingDateRange, CompanyTicker
from nps_crawling.utils.sec_query import SecParams

def extract_pdf_content(response: scrapy.http.Response) -> str:
    """Extracts content from PDF file."""
    pdf_bytes: bytes = response.body
    reader: pypdf.PdfReader = pypdf.PdfReader(io.BytesIO(pdf_bytes))

    text_parts: list[str] = []

    for page in reader.pages:
        page_text: str = page.extract_text() or ''
        text_parts.append(page_text)

    core_text: str = '\n'.join(text_parts)
    return core_text

def extract_xml_content(response: scrapy.http.Response) -> str:
    """Extracts content from HTML/XML file."""
    return response.text

class BetterSpider(scrapy.Spider):
    """Improved Scrapy Spider for improved filing search (simply better)."""
    name = 'better_spider'

    def __init__(self):
        """Initializes spider."""
        super(BetterSpider, self).__init__()
        # 'Hotkey' map for specific file types
        self.function_map: dict = {
            'pdf': extract_pdf_content,
            'xml': extract_xml_content,
            'html': extract_xml_content,
            'htm': extract_xml_content,
        }

    async def start(self) -> AsyncIterator[Any]:
        """Starts scrapy spider."""

        # Specifies company/ticker
        individual: CompanyTicker = CompanyTicker(ticker=['TAP', 'TAP-A'], cik='0000024545', title='MOLSON COORS BEVERAGE CO')
        # Creates parameters based on sec.gov search parameters
        sec_params = SecParams(query_base='https://efts.sec.gov/LATEST/search-index?',
                               keyword='net promoter score',
                               from_date='2001-01-01',
                               to_date='2026-02-19',
                               individual_search=individual,
                               date_range=FilingDateRange.ALL,
                               #filing_category=FilingsCategoryCollectionCoarse.ALL_ANUAL_QUARTERLY_AND_CURRENT_REPORTS,
                               #filing_categories=FilingCategoryCollection.filing_categories[FilingsCategoryCollectionCoarse.]
                               )
        # Creates query to fetch all related documents
        sec_query = SecQuery(sec_params=sec_params, limit=500)
        # Start query for filings
        sec_query.fetch_filings()

        # Iterate through all filings
        for filing in sec_query.keyword_filings:
            url: str = filing.get_url()[0]
            yield scrapy.Request(
                url=url,
                callback=self.parse,
                meta={'filing': filing}
            )

    def parse(self, response: scrapy.http.Response) -> Iterable[FilingItem]:
        """Parses filing and redirects to specific content extractor."""
        filing: Filing = response.meta['filing']

        # Extract text from response content
        text: str = self.function_map[filing.file_container_type](response)

        item: FilingItem = FilingItem()
        item['filing'] = filing
        item['core_text'] = text

        # Dispatch into pipeline
        yield item