import scrapy

class FilingItem(scrapy.Item):
    company = scrapy.Field()
    filing_url = scrapy.Field()
    content_excerpt = scrapy.Field()
    mention_count = scrapy.Field()
    filing_type = scrapy.Field()
    filing_date = scrapy.Field()
    full_html = scrapy.Field()