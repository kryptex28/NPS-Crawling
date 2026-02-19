from typing import Iterable, Any, AsyncIterator

import scrapy

from nps_crawling.crawler.items import FilingItem
from nps_crawling.utils.sec_query import SecQuery
from nps_crawling.utils.filings import Filing, FilingDateRange, CompanyTicker
from nps_crawling.utils.sec_query import SecParams


class BetterSpider(scrapy.Spider):

    name = 'better_spider'

    def __init__(self):

        super(BetterSpider, self).__init__()

    async def start(self) -> AsyncIterator[Any]:
        # Receive list of Filings
        individual: CompanyTicker = CompanyTicker(ticker=['TAP', 'TAP-A'], cik='0000024545', title='MOLSON COORS BEVERAGE CO')
        sec_params = SecParams(query_base='https://efts.sec.gov/LATEST/search-index?',
                               keyword='net promoter score',
                               from_date='2001-01-01',
                               to_date='2026-02-19',
                               individual_search=individual,
                               date_range=FilingDateRange.ALL,
                               #filing_category=FilingsCategoryCollectionCoarse.ALL_ANUAL_QUARTERLY_AND_CURRENT_REPORTS,
                               #filing_categories=FilingCategoryCollection.filing_categories[FilingsCategoryCollectionCoarse.]
                               )
        sec_query = SecQuery(sec_params=sec_params, limit=500)
        sec_query.fetch_filings()

        for filing in sec_query.keyword_filings:

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