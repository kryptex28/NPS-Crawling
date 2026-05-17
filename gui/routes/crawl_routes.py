from flask import Blueprint, jsonify, request, send_from_directory, Response, redirect, url_for, session
from middleware.auth import login_required
from services.crawl_service import initialize_crawl, event_stream
from nps_crawling.crawler.pre_fetch_utils.sec_params import SecSearchParams, get_search_params_from_id, create_search_params_from_config
from nps_crawling.crawler.pre_fetch_utils.sec_params import SecSearchParams
from nps_crawling.config import Config
from nps_crawling.utils.event_bus import bus
import json

import logging

logging.basicConfig(level=logging.INFO)
crawl_bp: Blueprint = Blueprint("crawl_routes", __name__)

@crawl_bp.get("/results")
@login_required
def results():
    return send_from_directory(".", "results.html")

@crawl_bp.get("/crawl")
@login_required
def check():
    return send_from_directory(".", "check.html")

@crawl_bp.post("/start-crawl")
@login_required
def start_crawl():
    id_list: list[str] = json.loads(session.get("selected_ids", []))
    parameters: list[str] = []

    for id in id_list:
        path: str = get_search_params_from_id(Config.GUI_QUERY_PATH, id=id)
        parameters.append(path)
    
    initialize_crawl(parameters)


    return jsonify({"status": "started"})

@crawl_bp.post("/stop-crawl")
@login_required
def stop_crawl():
    bus.publish("crawler.stop")
    return jsonify({"status": "stopped"})

@crawl_bp.post("/start-search")
@login_required
def start_search():
    data: dict = request.form.to_dict(flat=True)
    print(data)
    
    id_list: list[str] = data.get("ids", "")
    session["selected_ids"] = id_list
    return redirect(url_for("crawl_routes.check"))

@crawl_bp.post("/crawl")
@login_required
def search():
    data: dict = request.form.to_dict(flat=True)
    print(data)
    
    id_list: list[str] = data.get("ids", "")
    session["selected_ids"] = id_list
    return redirect(url_for("crawl_routes.check"))

@crawl_bp.get("/stream-crawl")
@login_required
def stream_crawl():
    logging.info(f"SSE client connected")
    return Response(event_stream(), mimetype='text/event-stream',
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})