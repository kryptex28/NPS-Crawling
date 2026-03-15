"""Entry point for the Flask web application."""
import json
import threading
import time
import os
import logging

from flask import Flask, jsonify, request, send_from_directory, Response, stream_with_context
import importlib.resources as pkg_resources

from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings

import nps_crawling
from nps_crawling.crawler.spiders.better_spider import BetterSpider
from nps_crawling.utils import filings
from nps_crawling.utils.sec_params import SecParams, create_sec_param_from_dict, create_config_from_params
from nps_crawling.utils.sec_query import SecQuery
from nps_crawling.utils.filings import Filing
from flask import Flask, jsonify, request, send_from_directory
from nps_crawling.crawler import CrawlerPipeline

app = Flask(__name__, static_folder=".", static_url_path="")
crawl_results = []
crawl_done = False
last_data = {}
data = {}


@app.get("/")
def index():
    """Serve the index.html file."""
    return send_from_directory(".", "index.html")


@app.get("/results")
def results():
    """Serve the results.html file."""
    return send_from_directory(".", "results.html")


@app.get("/check")
def check():
    """Serve the check.html file."""
    crawl_results.clear()

    thread = threading.Thread(target=start_search, args=(data,))
    # filings_found: list[Filing] = start_search(data)
    thread.daemon = True
    thread.start()
    #r = [f.to_json() for f in filings_found]
    #return jsonify(r)/
    #return jsonify({"status": "started"})
    return send_from_directory(".", "check.html")

import json

@app.get("/crawl-stream")
def crawl_stream():
    print("SSE client connected")
    return Response(event_stream(), mimetype='text/event-stream',
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
def event_stream():
    last_index = 0
    while True:
        while last_index < len(crawl_results):
            result = crawl_results[last_index]
            last_index += 1
            print(f"Yielding result {last_index}")
            yield f"data: {json.dumps(result)}\n\n"
        if crawl_done:
            yield 'data: {"__done": true}\n\n'
            print("Ending SSE")
            return
        time.sleep(0.5)

def filing_crawled(filing: Filing):
    global data
    data = filing.to_json()
    crawl_results.append(data)

@app.post("/search")
def search():
    """Handle search form submission."""
    global data
    data = request.form.to_dict(flat=True)

    return {}


logger = logging.getLogger(__name__)

def start_search(data: dict):
    """Handle search form submission."""

    """ 
    TODO: 
    MAYBE improve this code and use the CrawlerPipeline. The current state copies the whole logic
    in order to reduce redundancy. Status quo, this code works -- mostly. Though this is better than
    nothing so it will stay here for now.
    """
    global crawl_done
    global last_data
    crawl_done = False

    if not data == {}:
        last_data = data

    # Get the same query file which the crawler uses
    PACKAGE_ROOT = os.path.dirname(os.path.abspath(nps_crawling.__file__))
    SEC_QUERY_FILE_PATH = os.path.join(PACKAGE_ROOT, 'queries', 'query.json')

    param: SecParams = create_sec_param_from_dict(last_data)
    query_content = create_config_from_params([param])

    query: SecQuery = SecQuery(sec_params=param)

    os.environ['SCRAPY_SETTINGS_MODULE'] = 'nps_crawling.crawler.settings'

    # Overwrite query
    with open(SEC_QUERY_FILE_PATH, "w") as f:
        json.dump(query_content, f)

    settings = get_project_settings()

    settings.update({'LOG_LEVEL': logger.getEffectiveLevel()})

    print("=== Active Scrapy Settings ===")
    for name, value in settings.items():
        print(f"{name}: {value}")
    print("=== End of Settings ===\n")

    # Run spider
    process = CrawlerProcess(settings)

    process.crawl(BetterSpider,
                  callback=filing_crawled,
                  queries=[query],
                  )
    process.start()
    query.fetch_filings()

    crawl_done = True
    return query.keyword_filings

if __name__ == "__main__":
    app.run(debug=True)
