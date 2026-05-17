from flask import Blueprint, jsonify, request, send_from_directory, Response, redirect, url_for, session
from middleware.auth import login_required
from services.crawl_service import initialize_crawl, event_stream
from services.query_service import svc_create_query, svc_delete_query, svc_get_queries
from services.results_service import svc_export_results

from routes.static_routes import static_bp

import json
import logging

logging.basicConfig(level=logging.INFO)
results_bp: Blueprint = Blueprint("results_routes", __name__)


@results_bp.post("/export-results")
@login_required
def export_results():
    data: dict = request.form.to_dict(flat=True)
    format: str = data.get("format", "csv")
    svc_export_results(format=format)
    return {}

@results_bp.post("/results")
@results_bp.get("/results")
@login_required
def results():
    return send_from_directory(".", "results.html")
