from flask import Blueprint, jsonify, request, send_from_directory, Response
from middleware.auth import login_required
from services.crawl_service import initialize_crawl, event_stream
from services.query_service import svc_create_query, svc_delete_query, svc_get_queries

import logging

logging.basicConfig(level=logging.INFO)
query_bp: Blueprint = Blueprint("query_routes", __name__)


@query_bp.post("/create-query")
@login_required
def create_query():
    data: dict = request.form.to_dict(flat=True)
    data["filing_types"] = request.form.getlist("filing_types")

    svc_create_query(data)
    return jsonify({"status": True})

@query_bp.post("/delete-query")
@login_required
def delete_query():
    # query id from payload
    # delete_query(id)
    return jsonify({"status": True})

@query_bp.get("/get-queries")
@login_required
def get_queries():
    queries: list[dict] = svc_get_queries()

    return jsonify({ "results": queries })