from flask import Blueprint, send_from_directory
from middleware.auth import login_required

static_bp: Blueprint = Blueprint("static_routes", __name__)

@static_bp.route("/thu_logo.png")
def thu_logo():
    return send_from_directory(".", "thu_logo.png")

@static_bp.route("/styles.css")
def styles():
    return send_from_directory(".", "styles.css")

@static_bp.route("/")
@login_required
def index():
    return send_from_directory(".", "index.html")

@static_bp.route("/debug")
@login_required
def debug():
    return "Now you see me!"