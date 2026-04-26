import threading
import logging
import time

from flask import json

from nps_crawling.utils.event_bus import bus
from nps_crawling.crawler import CrawlerPipeline
from nps_crawling.crawler.pre_fetch_utils.filings import Filing

logger = logging.getLogger(__name__)

crawl_results: list = []
crawl_done: bool = False
last_data: dict = {}

def on_crawl_done(filing: Filing):
    crawl_results.append(filing)
    print("Received crawl result:", filing.file_path_name)

def on_crawl_received(filing: Filing):
    data = filing.to_json()
    crawl_results.append(data)
    print("Received crawl result:", filing.file_path_name)

bus.subscribe("crawl.done", on_crawl_done)
bus.subscribe("crawl.result", on_crawl_received)

def initialize_crawl(data: dict):
    global crawl_done

    crawl_results.clear()
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
    last_index: int = 0

    try:
        while True:
            while last_index < len(crawl_results):
                result = crawl_results[last_index]
                last_index += 1
                logger.info(f"Yielding result {last_index}")
                yield f"data: {json.dumps(result)}\n\n"
            
            if crawl_done:
                logger.info("Crawl done, yielding final event")
                yield 'data: {"__done": true}\n\n'
                return
            time.sleep(0.5)
    except Exception as e:
        logger.error(f"Error in event stream: {e}", exc_info=True)
        yield f'data: {json.dumps({"__error": str(e)})}\n\n'
