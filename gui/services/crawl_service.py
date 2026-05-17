import threading
import logging
import time
import queue

from flask import json

from nps_crawling.utils.event_bus import bus
from nps_crawling.crawler import CrawlerPipeline
from nps_crawling.crawler.pre_fetch_utils.filings import Filing
from nps_crawling.crawler.pre_fetch_utils.sec_query import SecQuery
from nps_crawling.db.db_adapter import DbAdapter

logger = logging.getLogger(__name__)

crawl_dict: dict = {}
crawl_done: bool = False
last_data: dict = {}
prefetch_done: bool = False
updated_ids: set = set()

thread: threading.Thread = threading.Thread()

crawl_queue: queue.Queue = queue.Queue()

def on_crawl_done(filing: Filing):
    crawl_queue.put({"__done": True})

def on_crawl_received(filing: Filing):
    crawl_queue.put({
        "type": "crawl",
        "id": filing.get_id(),
        "status": "crawled",
        **filing.to_json()
    })
    logger.info(f"Marked { filing.get_id() } as crawled")


def on_prefetch_received(filings: list[Filing]):
    for filing in filings:
        crawl_queue.put({
            "type": "prefetch",
            "id": filing.get_id(),
            "status": "prefetched",
            **filing.to_json()
        })
        logger.info(f"Received prefetch result: { filing.get_id() }")

def on_paging_info(page: int, total: int):
    crawl_queue.put({ "type": "paging", "page": page, "total": total })

def on_crawler_status(info: str, details: str):
    crawl_queue.put({ "type": "crawler", "status": info, "details": details })

def on_crawler_duplicates(filings: list[Filing]):
    for filing in filings:
        crawl_queue.put({
                "type": "prefetch",
                "id": filing.get_id(),
                "status": "database",
                **filing.to_json()
            })
        logger.info(f"Marked { filing.get_id() } as database")


bus.subscribe("crawl.done", on_crawl_done)
bus.subscribe("crawl.result", on_crawl_received)
bus.subscribe("prefetch.result", on_prefetch_received)
bus.subscribe("paging.info", on_paging_info)
bus.subscribe("crawler.status", on_crawler_status)
bus.subscribe("crawler.duplicates", on_crawler_duplicates)


def initialize_crawl(ids: list[str]):
    global thread 
    while not crawl_queue.empty():
        crawl_queue.get_nowait()

    thread = threading.Thread(target=_run_crawl, args=(ids, ))
    thread.daemon = True
    thread.start()

def _run_crawl(ids: list[str]) -> None:
    crawler = CrawlerPipeline()
    crawler.crawler_workflow(search_parameter_files=ids)

def event_stream():
    while True:
        try:
            data = crawl_queue.get(timeout=30)
            yield f"data: { json.dumps(data) }\n\n"

            if data.get("__done"):
                return
            
        except queue.Empty:
            yield f'data: {"__heartbeat: true"}\n\n'
        except Exception as e:
            logger.error(f"Error in event stream: {e}", exc_info=True)
            yield f"data: { json.dumps({"__error": str(e)} )}\n\n"