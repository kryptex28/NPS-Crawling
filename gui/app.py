"""Entry point for the Flask web application."""
import json
import threading
import time

from flask import Flask, jsonify, request, send_from_directory, Response, stream_with_context

from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings

from nps_crawling.crawler.spiders.better_spider import BetterSpider
from nps_crawling.utils import filings
from nps_crawling.utils.sec_params import SecParams, create_sec_param_from_dict
from nps_crawling.utils.sec_query import SecQuery
from nps_crawling.utils.filings import Filing
from flask import Flask, jsonify, request, send_from_directory

app = Flask(__name__, static_folder=".", static_url_path="")
crawl_results = []

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
    return send_from_directory(".", "check.html")

import json

@app.get("/crawl-stream")
def crawl_stream():
    print("SSE client connected")

    def event_stream():
        last_index = 0
        while True:
            while last_index < len(crawl_results):
                result = crawl_results[last_index]
                last_index += 1
                print(f"Yielding result {last_index}")
                yield f"data: {json.dumps(result)}\n\n"  # <-- serialize here
            time.sleep(0.5)

    return Response(event_stream(), mimetype='text/event-stream',
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


def filing_crawled(filing: Filing):
    data = filing.to_json()
    crawl_results.append(data)

@app.post("/search")
def search():
    """Handle search form submission."""
    crawl_results.clear()
    data = request.form.to_dict(flat=True)

    thread = threading.Thread(target=start_search, args=(data,))
    filings_found: list[Filing] = start_search(data)
    thread.daemon = True
    thread.start()
    #r = [f.to_json() for f in filings_found]
    #return jsonify(r)
    return jsonify({"status": "started"})

def start_search(data: dict):
    param: SecParams = create_sec_param_from_dict(data)

    query: SecQuery = SecQuery(sec_params=param)
    process = CrawlerProcess(get_project_settings())

    process.crawl(BetterSpider,
                  callback=filing_crawled,
                  queries=[query],
                  )
    process.start()
    query.fetch_filings()
    return query.keyword_filings

if __name__ == "__main__":
    app.run(debug=True)
