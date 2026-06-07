from flask import Blueprint, jsonify, request, send_from_directory, Response, redirect, url_for
from middleware.auth import login_required
from services.crawl_service import initialize_crawl, event_stream
from services.query_service import svc_create_query, svc_delete_query, svc_get_queries

from routes.static_routes import static_bp

import logging

logging.basicConfig(level=logging.INFO)
query_bp: Blueprint = Blueprint("query_routes", __name__)


@query_bp.post("/create-query")
def create_query():
    data: dict = request.form.to_dict(flat=True)
    data["filing_types"] = request.form.getlist("filing_types")

    status = svc_create_query(data)
    return jsonify({"status": status})

@query_bp.post("/delete-query")
def delete_query():
    data: dict = request.get_json()
    status: bool = svc_delete_query(data["id"])

    return jsonify({"status": status })

@query_bp.get("/get-queries")
def get_queries():
    queries: list[dict] = svc_get_queries()

    return jsonify({ "results": queries })