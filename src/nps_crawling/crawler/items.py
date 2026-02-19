"""Crawler items definition."""

import scrapy

from nps_crawling.utils.filings import Filing


class FilingItem(scrapy.Item):
    """Item representing a filing with potential NPS mentions."""
    filing: Filing = scrapy.Field()
    core_text: str = scrapy.Field()
    keyword: str = scrapy.Field()