"""Entry point for the Flask web application."""
from flask import Flask, jsonify, request, send_from_directory
from functools import wraps
from nps_crawling.db.db_adapter import DbAdapter

import logging

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

PREFIX = "/services/hub-flask"

application = Flask(__name__,
                    static_folder="static",
                    static_url_path=f"{PREFIX}/static")

from routes.static_routes import static_bp
from routes.crawl_routes import crawl_bp

application.register_blueprint(static_bp, url_prefix=PREFIX)
application.register_blueprint(crawl_bp, url_prefix=PREFIX)

if __name__ == "__main__":
    # Wir nutzen Port 5000 und Host 0.0.0.0 wie von der Admin gefordert
    logger.info(f"Starting Flask application on http://0.0.0.0:5000")

    DbAdapter().ensure_table_exists()
    application.run(host="0.0.0.0", port=5000, debug=False)