from flask import Flask, jsonify, request, send_from_directory
from functools import wraps
import os

application = Flask(__name__)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # DEBUG: Zeigt dir im Terminal an, welche Cookies wirklich ankommen
        # print("Vorhandene Cookies:", request.cookies) 
        
        # Falls der spezifische Jupyter-Cookie nicht gefunden wird, 
        # lassen wir es für den ersten Test mal etwas lockerer:
        if not request.cookies:
            return "Please log in with a valid username (No cookies found).", 401
        
        return f(*args, **kwargs)
    return decorated_function

# --- Routen mit Prefix ---
PREFIX = "/services/hub-flask"

@application.route(f"{PREFIX}/thu_logo.png")
def thu_logo():
    return send_from_directory(".", "thu_logo.png")

@application.route(f"{PREFIX}/styles.css")
def styles():
    return send_from_directory(".", "styles.css")

@application.route(f"{PREFIX}/")
@login_required
def index():
    return send_from_directory(".", "index.html")

@application.get(f"{PREFIX}/results")
@login_required
def results():
    return send_from_directory(".", "results.html")

@application.get(f"{PREFIX}/check")
@login_required
def check():
    return send_from_directory(".", "check.html")

@application.post(f"{PREFIX}/search")
@login_required
def search():
    data = request.form.to_dict(flat=True)
    data["filing_types"] = request.form.getlist("filing_types")
    return jsonify(data)

# --- DIESER TEIL FEHLTE NOCH ---
if __name__ == "__main__":
    # Wir nutzen Port 5000 und Host 0.0.0.0 wie von der Admin gefordert
    application.run(host="0.0.0.0", port=5000, debug=False)