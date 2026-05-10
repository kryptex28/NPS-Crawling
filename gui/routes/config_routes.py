from flask import Blueprint, jsonify, request, send_from_directory, Response, redirect, url_for
from middleware.auth import login_required
from services.config_service import update_config_from_dict
from routes.static_routes import static_bp

import logging

logging.basicConfig(level=logging.INFO)
config_bp: Blueprint = Blueprint("config_routes", __name__)


@config_bp.post("/set-config")
@login_required
def set_config():
    data: dict = request.form.to_dict(flat=True)

    print(data)
    update_config_from_dict(data=data)

    return {}