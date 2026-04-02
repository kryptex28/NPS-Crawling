import os
from collections import defaultdict

from nps_crawling.crawler.utils import CrawlerPipeline
from nps_crawling.utils.filings import Filing

SEC_QUERY_DIR_PATH = os.path.join("/home/leonv/Projects/NPS-Crawling/src/nps_crawling/", 'queries')

pipeline: CrawlerPipeline = CrawlerPipeline()
filings: list[Filing] = pipeline.prefetch_data(query_path=SEC_QUERY_DIR_PATH)

occurences: dict = defaultdict(int)

for filing in filings:
    occurences[filing.file_container_type] += 1

print(dict(occurences))