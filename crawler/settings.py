BOT_NAME = "crawler"
SPIDER_MODULES = ["crawler.spiders"]
NEWSPIDER_MODULE = "crawler.spiders"

USER_AGENT = "DataResearchBot (contact: your.email@example.com)" # TODO
ROBOTSTXT_OBEY = True

ITEM_PIPELINES = {
    'crawler.pipelines.cleaning.CleanTextPipeline': 300,
    'crawler.pipelines.filtering.NpsMentionFilterPipeline': 400,
    'crawler.pipelines.storage.SaveToJSONPipeline': 500,
}

DOWNLOAD_DELAY = 1.0  # Limit so SEC doesn't explode and API bans

FEEDS = {
    'filings.jsonl': {'format': 'jsonlines'},
}