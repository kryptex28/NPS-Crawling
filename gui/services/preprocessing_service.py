from nps_crawling.preprocessing.utils import PreProcessingPipeline
from nps_crawling.db.db_adapter import DbAdapter

import threading
import queue
import json
import logging
import time

logger: logging.Logger = logging.getLogger("__name__")
data_queue: queue.Queue = queue.Queue()

is_preprocessing: bool = False
sync_delay: int = 10

def svc_start_preprocessing():
    global is_preprocessing
    is_preprocessing = True
    thread: threading.Thread = threading.Thread(target=_start_preprocessing, daemon=True)
    sync_thread: threading.Thread = threading.Thread(target=_sync_data, daemon=True)

    thread.start()
    # sync_thread.start()

def _sync_data():
    is_sync_active: bool = True

    cache: dict = {}
    while is_sync_active:
        db: DbAdapter = DbAdapter()

        try:
            data: list[dict] = db.get_all_filings()
            
            for filing in data:
                if filing.get("path_to_preprocessed"):
                    if cache.get(filing.get("id")):
                        data_queue.put({"data": {"filing_id": filing.get("id")}})
                        cache[filing.get("id")] = True

            time.sleep(sync_delay)
        except Exception as e: 
            is_sync_active = False
            logger.exception(e, exc_info=True)


def _start_preprocessing():
    global is_preprocessing
    preprocessing: PreProcessingPipeline = PreProcessingPipeline()

    preprocessing.pre_processing_workflow()
    data_queue.put({"__done": True})
    is_preprocessing = False

def svc_stream_preprocessing():
    while True:
        try:
            data = data_queue.get(timeout=30)
            yield f"data: { json.dumps(data) }\n\n"

            if data.get("__done") or not is_preprocessing:
                return
            
        except queue.Empty:
            yield f'data: {"__heartbeat: true"}\n\n'
        except Exception as e:
            logger.error(f"Error in event stream: {e}", exc_info=True)
            yield f"data: { json.dumps({"__error": str(e)} )}\n\n"
