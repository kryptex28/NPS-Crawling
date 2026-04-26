import threading
import logging
import time

from flask import json

from nps_crawling.utils.event_bus import bus
from nps_crawling.crawler import CrawlerPipeline
from nps_crawling.crawler.pre_fetch_utils.filings import Filing

logger = logging.getLogger(__name__)

crawl_dict: dict = {}
crawl_done: bool = False
last_data: dict = {}
prefetch_done: bool = False
updated_ids: set = set()

def on_crawl_done(filing: Filing):
    if filing.get_id() in crawl_dict:
        logger.info(f"Updating crawl result for {filing.get_id()}")
        crawl_dict[filing.get_id()]["status"] = "crawled"
        data = filing.to_json()
        data["status"] = "crawled"

def on_crawl_received(filing: Filing):
    if filing.get_id() in crawl_dict:
        logger.info(f"Updating crawl result for {filing.get_id()}")
        crawl_dict[filing.get_id()]["status"] = "crawled"
        updated_ids.add(filing.get_id())  # mark as needing re-send
        logger.info(f"Marked {filing.get_id()} as crawled")

def on_prefetch_received(filings: list[Filing]):
    for filing in filings:
        crawl_dict[filing.get_id()] = filing.to_json()
        crawl_dict[filing.get_id()]["status"] = "prefetched"
        logger.info(f"Received prefetch result: {filing.get_id()}")

bus.subscribe("crawl.done", on_crawl_done)
bus.subscribe("crawl.result", on_crawl_received)
bus.subscribe("prefetch.result", on_prefetch_received)

def initialize_crawl(data: dict):
    global crawl_done

    crawl_dict.clear()
    thread: threading.Thread = threading.Thread(target=_run_crawl, args=(data, ))
    thread.daemon = True
    thread.start()

def _run_crawl(data: dict) -> None:
    global crawl_done, last_data

    if data:
        last_data = data
    
    crawler = CrawlerPipeline()
    crawler.crawler_workflow()
    crawl_done = True

def event_stream():
    last_prefetch_cound = 0
    send_ids: set = set()

    try:
        while True:

            current_keys = list(crawl_dict.keys())
            for filing_id in current_keys:
                if filing_id not in send_ids:
                    result = crawl_dict[filing_id]
                    logger.info(f"Yielding new result for ID {filing_id}")
                    yield f"data: {json.dumps(result)}\n\n"
                    send_ids.add(filing_id)

            for filing_id in list(updated_ids):
                result = crawl_dict.get(filing_id)
                logger.info(f"Yielding updated result for ID {filing_id}")
                yield f"data: {json.dumps(result)}\n\n"
                updated_ids.remove(filing_id)

            if crawl_done:
                logger.info("Crawl done, yielding final event")
                yield 'data: {"__done": true}\n\n'
                return
            
            time.sleep(0.5)
    except Exception as e:
        logger.error(f"Error in event stream: {e}", exc_info=True)
        yield f'data: {json.dumps({"__error": str(e)})}\n\n'
