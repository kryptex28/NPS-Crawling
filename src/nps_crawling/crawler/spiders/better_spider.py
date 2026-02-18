from typing import Iterable, Any, AsyncIterator

import requests
import scrapy

from nps_crawling.crawler.items import FilingItem
from nps_crawling.utils.sec_extractor import SecQuery
from nps_crawling.utils.filings import Filing, FilingDateRange
from nps_crawling.utils.filings import FilingsCategoryCollectionCoarse
from nps_crawling.utils.filings import FilingCategoryCollection
from nps_crawling.utils.sec_query import SecParams


class BetterSpider(scrapy.Spider):

    name = 'better_spider'

    def __init__(self):

        super(BetterSpider, self).__init__()

    async def start(self) -> AsyncIterator[Any]:
        # Receive list of Filings
        sec_params = SecParams(keywords=['NPS'],
                               from_date='2016-02-18',
                               to_date='2026-02-18',
                               date_range=FilingDateRange.LAST_10_YEARS,
                               filing_category=FilingsCategoryCollectionCoarse.ALL_ANUAL_QUARTERLY_AND_CURRENT_REPORTS,
                               filing_categories=FilingCategoryCollection.filing_categories[FilingsCategoryCollectionCoarse.ALL_ANUAL_QUARTERLY_AND_CURRENT_REPORTS])
        sec_query = SecQuery(sec_params)
        sec_query.fetch_filings()
        filings = []
        for filing in filings:

            yield scrapy.Request(
                url=filing.get_url()[0],
                callback=self.parse,
                meta={'filing': filing}
            )

    def parse(self, response):
        filing = response.meta['filing']
    
        item = FilingItem()
        item['company'] = filing.adsh
        item['ticker'] = filing.id
        item['cik'] = filing.ciks[0]
        item['keywords_found'] = []
        item['html_text'] = response.body

        print(type(item))

        yield item