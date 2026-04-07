"""Entry point for the Flask web application."""
from flask import Flask, jsonify, request, send_from_directory
from functools import wraps

application = Flask(__name__)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "jupyterhub-session-id" not in request.cookies:
            return "Please log in with a valid username.", 401
        return f(*args, **kwargs)
    return decorated_function

@application.route("/services/hub-flask/thu_logo.png")
@login_required
def thu_logo():
    return send_from_directory(".", "thu_logo.png")

@application.route("/services/hub-flask/styles.css")
@login_required
def styles():
    return send_from_directory(".", "styles.css")

@application.route("/services/hub-flask/")
@login_required
def index():
    return send_from_directory(".", "index.html")

@application.route("/services/hub-flask/debug")
@login_required
def debug():
    return "Now you see me!"


@application.get("/services/hub-flask/results")
@login_required
def results():
    """Serve the results.html file."""
    return send_from_directory(".", "results.html")


@application.get("/services/hub-flask/check")
@login_required
def check():
    """Serve the check.html file."""
    return send_from_directory(".", "check.html")


@application.post("/services/hub-flask/search")
@login_required
def search():
    """Handle search form submission."""
    data = request.form.to_dict(flat=True)
    data["filing_types"] = request.form.getlist("filing_types")
    return jsonify(data)
