from flask import Blueprint, jsonify, request, send_from_directory, Response, redirect, url_for, session
from middleware.auth import login_required
from services.classification_service import svc_start_classification, svc_stream_classification
from routes.static_routes import static_bp

import json
import logging

logging.basicConfig(level=logging.INFO)
classification_bp: Blueprint = Blueprint("classification_routes", __name__)


@classification_bp.post("/start-classification")
def start_classification():
    svc_start_classification()
    return {}

@classification_bp.post("/classification")
@classification_bp.get("/classification")
def classification():
    return send_from_directory(".", "classification.html")


@classification_bp.get("/stream-classification")
def stream_classification():
    logging.info(f"SSE client connected")
    return Response(svc_stream_classification(), mimetype='text/event-stream',
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})