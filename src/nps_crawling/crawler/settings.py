"""Scrapy settings for crawler project."""

BOT_NAME = "crawler"
SPIDER_MODULES = ["nps_crawling.crawler.spiders"]
NEWSPIDER_MODULE = "nps_crawling.crawler.spiders"

USER_AGENT = "DataResearchBot (contact: your.email@example.com)"  # TODO
ROBOTSTXT_OBEY = True

ITEM_PIPELINES = {
    'nps_crawling.crawler.pipelines.cleaning.CleanTextPipeline': 300,
    'nps_crawling.crawler.pipelines.filtering.NpsMentionFilterPipeline': 400,
    'nps_crawling.crawler.pipelines.storage.SaveToJSONPipeline': 500,
}

DOWNLOAD_DELAY = 1.0  # Limit so SEC doesn't explode and API bans

# LOG_LEVEL = 'INFO'
# LOG_FORMAT = '%(asctime)s [%(name)s] %(levelname)s: %(message)s'
# LOG_DATEFORMAT = '%Y-%m-%d %H:%M:%S'
# LOG_ENABLED = True

STATS_DUMP = True
JOBDIR = 'crawls/sec_filings_spider'
