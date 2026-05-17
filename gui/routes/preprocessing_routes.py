from flask import Blueprint, jsonify, request, send_from_directory, Response, redirect, url_for, session
from middleware.auth import login_required
from services.crawl_service import initialize_crawl, event_stream
from services.query_service import svc_create_query, svc_delete_query, svc_get_queries
from services.preprocessing_service import svc_start_preprocessing, svc_stream_preprocessing

from routes.static_routes import static_bp

import json
import logging

logging.basicConfig(level=logging.INFO)
preprocessing_bp: Blueprint = Blueprint("preprocessing_routes", __name__)


@preprocessing_bp.post("/start-preprocessing")
@login_required
def start_preprocessing():
    svc_start_preprocessing()
    return {}

@preprocessing_bp.post("/preprocessing")
@preprocessing_bp.get("/preprocessing")
@login_required
def preprocessing():
    return send_from_directory(".", "preprocessing.html")


@preprocessing_bp.get("/stream-preprocessing")
@login_required
def stream_crawl():
    logging.info(f"SSE client connected")
    return Response(svc_stream_preprocessing(), mimetype='text/event-stream',
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})