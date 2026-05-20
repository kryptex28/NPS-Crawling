from nps_crawling.db.db_adapter import DbAdapter
import logging
import threading
import queue
import json
from datetime import date, datetime

data_queue: queue.Queue = queue.Queue()

def svc_show_entries():
    db_thread: threading.Thread = threading.Thread(target=_fetch_entries_from_db)
    db_thread.start()


def _fetch_entries_from_db():
    db_adapter: DbAdapter = DbAdapter()
    data: list[dict] = []
    try:
        data = db_adapter.get_all_filings()
    except Exception as e:
        logging.error(f"Error fetching entries from database: {e}")

    for entry in data:
        data_queue.put(entry)

def svc_stream_entries():
    while True:
        try:
            entry = data_queue.get(timeout=5)
            yield f"data: {json.dumps(entry, cls=DateEncoder)}\n\n".encode("utf-8")
        except queue.Empty:
            break

class DateEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):  # datetime before date — datetime is a subclass of date
            return obj.isoformat()     # e.g. "2026-05-03T07:29:59.654770+00:00"
        if isinstance(obj, date):
            return obj.isoformat()     # e.g. "2024-01-29"
        return super().default(obj)