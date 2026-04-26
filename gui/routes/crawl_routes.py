from flask import Blueprint, jsonify, request, send_from_directory, Response
from middleware.auth import login_required
from services.crawl_service import initialize_crawl, event_stream

import logging

logging.basicConfig(level=logging.INFO)
crawl_bp: Blueprint = Blueprint("crawl_routes", __name__)

@crawl_bp.get("/results")
@login_required
def results():
    return send_from_directory(".", "results.html")

@crawl_bp.get("/check")
@login_required
def check():
    return send_from_directory(".", "check.html")

@crawl_bp.post("/start-crawl")
@login_required
def start_crawl():
    from services.crawl_service import initialize_crawl, last_data, crawl_done
    if not last_data:
        return jsonify({"error": "No search data available. Please perform a search first."}), 400
    initialize_crawl(last_data)
    return jsonify({"status": "started"})

@crawl_bp.post("/stop-crawl")
@login_required
def stop_crawl():
    from services.crawl_service import crawl_done
    import services.crawl_service as cs
    cs.crawl_done = True
    return jsonify({"status": "stopped"})

@crawl_bp.post("/search")
@login_required
def search():
    data = request.form.to_dict(flat=True)
    data["filing_types"] = request.form.getlist("filing_types")

    from services.crawl_service import last_data
    last_data.clear()
    last_data.update(data)
    return send_from_directory(".", "check.html")

@crawl_bp.get("/stream-crawl")
@login_required
def stream_crawl():
    logging.info(f"SSE client connected")
    return Response(event_stream(), mimetype='text/event-stream',
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})