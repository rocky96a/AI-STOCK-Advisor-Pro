"""
Route protection.

`@token_required` wraps any Flask view and rejects the request with a 401
JSON response unless a valid `Authorization: Bearer <token>` header is
present. Apply this to every API route that should not work before login.
"""

from functools import wraps
from flask import request, jsonify, g

from backend.auth.token_service import verify_token


def _extract_token():
    auth_header = request.headers.get("Authorization", "")

    if auth_header.startswith("Bearer "):
        return auth_header[len("Bearer "):].strip()

    # Fallback so the token also works as a query param, e.g. for the
    # EventSource/websocket-style calls that can't set custom headers.
    return request.args.get("token")


def token_required(view_func):
    @wraps(view_func)
    def wrapped(*args, **kwargs):
        token = _extract_token()
        payload = verify_token(token)

        if not payload or not payload.get("username"):
            return jsonify({
                "success": False,
                "error": "Unauthorized",
                "message": "Login required. Please sign in to continue.",
            }), 401

        g.current_user = payload["username"]

        return view_func(*args, **kwargs)

    return wrapped
