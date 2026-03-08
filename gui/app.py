from flask import Flask, jsonify, request, send_from_directory
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings

from nps_crawling.crawler.spiders.better_spider import BetterSpider
from nps_crawling.utils.sec_params import SecParams, create_sec_param_from_dict
from nps_crawling.utils.sec_query import SecQuery
from nps_crawling.utils.filings import Filing

app = Flask(__name__, static_folder=".", static_url_path="")


@app.get("/")
def index():
    return send_from_directory(".", "index.html")


@app.get("/results")
def results():
    return send_from_directory(".", "results.html")


@app.get("/check")
def check():
    return send_from_directory(".", "check.html")


@app.post("/search")
def search():
    data = request.form.to_dict(flat=True)
    #data["filing_types"] = request.form.getlist("filing_types")
    filings_found: list[Filing] = start_search(data)
    r = [f.to_json() for f in filings_found]
    return jsonify(r)

def start_search(data: dict):
    param: SecParams = create_sec_param_from_dict(data)

    params: list[SecParams] = [param]
    #process = CrawlerProcess(get_project_settings())
    #process.crawl(BetterSpider, params=params)

    query: SecQuery = SecQuery(sec_params=param)
    query.fetch_filings()
    return query.keyword_filings

if __name__ == "__main__":
    app.run(debug=True)
