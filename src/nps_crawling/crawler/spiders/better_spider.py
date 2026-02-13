import requests
import scrapy

from nps_crawling.utils.sec_extractor import get_sec_data
from nps_crawling.utils.filings import Filing

class BetterSpider(scrapy.Spider):

    name = 'better_spider'

    def __init__(self):

        super(BetterSpider, self).__init__()

        # Receive list of Filings
        filings: list[Filing] = get_sec_data()

        #TODO: For each filing in that list, do:
        # get the url
        # dispatch for each url a crawl process