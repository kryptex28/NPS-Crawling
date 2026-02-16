from typing import Iterable, Any, AsyncIterator

import requests
import scrapy

from nps_crawling.crawler.items import FilingItem
from nps_crawling.utils.sec_extractor import get_sec_data
from nps_crawling.utils.filings import Filing

class BetterSpider(scrapy.Spider):

    name = 'better_spider'

    def __init__(self):

        super(BetterSpider, self).__init__()

    async def start(self) -> AsyncIterator[Any]:
        # Receive list of Filings
        filings: list[Filing] = get_sec_data(keywords=['NPS'])

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