from functools import wraps
from flask import request

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        #if "jupyterhub-session-id" not in request.cookies:
        #    return "Please log in with a valid username.", 401
        return f(*args, **kwargs)
    return decorated_function