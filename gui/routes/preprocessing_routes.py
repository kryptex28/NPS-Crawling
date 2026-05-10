from flask import Blueprint, jsonify, request, send_from_directory, Response, redirect, url_for, session
from middleware.auth import login_required
from services.crawl_service import initialize_crawl, event_stream
from services.query_service import svc_create_query, svc_delete_query, svc_get_queries

from routes.static_routes import static_bp

import json
import logging

logging.basicConfig(level=logging.INFO)
preprocessing_bp: Blueprint = Blueprint("preprocessing_routes", __name__)


@preprocessing_bp.post("/start-preprocessing")
@login_required
def start_preprocessing():
    data: dict = request.form.to_dict(flat=True)
    print(data)

    id_list: list[str] = data.get("ids", "")
    session["filing_ids"] = id_list
    return redirect(url_for("preprocessing_routes.preprocessing"))

@preprocessing_bp.get("/preprocessing")
@login_required
def preprocessing():
    return send_from_directory(".", "preprocessing.html")