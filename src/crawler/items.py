import scrapy


class FilingItem(scrapy.Item):
    company = scrapy.Field()
    ticker = scrapy.Field()
    cik = scrapy.Field()
    filing_url = scrapy.Field()
    keywords_found = scrapy.Field()
    html_text = scrapy.Field()