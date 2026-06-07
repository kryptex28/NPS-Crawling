from flask import Blueprint, jsonify, request, send_from_directory, Response, redirect, url_for, session
from middleware.auth import login_required
from services.db_service import svc_show_entries, svc_stream_entries

import logging

logging.basicConfig(level=logging.INFO)
db_bp: Blueprint = Blueprint("db_routes", __name__)

@db_bp.get("/database")
def db():
    return send_from_directory(".", "database.html")

@db_bp.post("/database-entries")
def database_entries():
    svc_show_entries()
    return redirect(url_for("db_routes.db"))

@db_bp.get("/database-stream")
def database_stream():
    svc_show_entries()
    logging.info(f"SSE client connected")
    return Response(svc_stream_entries(), mimetype='text/event-stream',
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})