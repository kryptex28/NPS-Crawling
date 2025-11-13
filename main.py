from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings
from crawler.spiders.sec_filings_spider import SECNpsSpider

import os
os.environ['SCRAPY_SETTINGS_MODULE'] = 'crawler.settings'

settings = get_project_settings()

print("=== Active Scrapy Settings ===")
for name, value in settings.items():
    print(f"{name}: {value}")
print("=== End of Settings ===\n")

# Run spider
process = CrawlerProcess(settings)
process.crawl(SECNpsSpider)
process.start()