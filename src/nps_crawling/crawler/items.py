"""Crawler items definition."""

import scrapy


class FilingItem(scrapy.Item):
    """Item representing a filing with potential NPS mentions."""
    company = scrapy.Field()
    ticker = scrapy.Field()
    cik = scrapy.Field()
    filing_url = scrapy.Field()
    keywords_found = scrapy.Field()
    html_text = scrapy.Field()

class BetterFilingItem(scrapy.Item):
    filing_id = scrapy.Field()
    company = scrapy.Field()
    filing_type = scrapy.Field()
    filing_date = scrapy.Field()
    file_urls = scrapy.Field()
    html_text = scrapy.Field()
    keywords = scrapy.Field()