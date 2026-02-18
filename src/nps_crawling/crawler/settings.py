"""Scrapy settings for crawler project.

This module contains Scrapy configuration used by the crawler spider in the
NPS-Crawling project.
"""

import os

BOT_NAME = "crawler"
SPIDER_MODULES = ["nps_crawling.crawler.spiders"]
NEWSPIDER_MODULE = "nps_crawling.crawler.spiders"

USER_AGENT = os.getenv("NPS_CRAWLER_USER_AGENT", "NPSCrawler/1.0 (contact: please-set-contact@example.com)")
DEFAULT_REQUEST_HEADERS = {
    "User-Agent": USER_AGENT,
}
ROBOTSTXT_OBEY = False

ITEM_PIPELINES = {
    'nps_crawling.crawler.pipelines.cleaning.CleanTextPipeline': 300,
    'nps_crawling.crawler.pipelines.filtering.NpsMentionFilterPipeline': 400,
    'nps_crawling.crawler.pipelines.storage.SaveToParquetPipeline': 500,
}

DOWNLOAD_DELAY = .2  # Limit so SEC doesn't explode and API bans

# LOG_LEVEL = 'INFO'
# LOG_FORMAT = '%(asctime)s [%(name)s] %(levelname)s: %(message)s'
# LOG_DATEFORMAT = '%Y-%m-%d %H:%M:%S'
# LOG_ENABLED = True

STATS_DUMP = True
JOB_DIR = 'crawls/sec_filings_spider'
