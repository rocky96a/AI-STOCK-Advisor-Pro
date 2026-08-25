from flask import Blueprint, request, jsonify

from backend.auth import user_store
from backend.auth.token_service import generate_token
from backend.auth.decorators import token_required

auth_api = Blueprint("auth_api", __name__)


@auth_api.route("/login", methods=["POST"])
def login():
    payload = request.get_json(silent=True) or {}

    username = str(payload.get("username", "")).strip()
    password = str(payload.get("password", ""))

    if not username or not password:
        return jsonify({
            "success": False,
            "error": "username and password are required",
        }), 400

    user = user_store.verify_credentials(username, password)

    if not user:
        return jsonify({
            "success": False,
            "error": "Invalid username or password",
        }), 401

    token = generate_token(user["username"])

    return jsonify({
        "success": True,
        "token": token,
        "user": {"username": user["username"]},
    })


@auth_api.route("/register", methods=["POST"])
def register():
    payload = request.get_json(silent=True) or {}

    username = str(payload.get("username", "")).strip()
    password = str(payload.get("password", ""))

    try:
        user_store.create_user(username, password)
    except ValueError as exc:
        return jsonify({
            "success": False,
            "error": str(exc),
        }), 400

    token = generate_token(username)

    return jsonify({
        "success": True,
        "token": token,
        "user": {"username": username},
    }), 201


@auth_api.route("/logout", methods=["POST"])
@token_required
def logout():
    # Tokens are stateless (signed, not stored server-side), so there is
    # nothing to invalidate here - the frontend simply discards the token.
    # This endpoint exists so the client has a clean, auditable "logout"
    # call, and so it stays consistent with the token-required pattern.
    return jsonify({"success": True})


@auth_api.route("/me", methods=["GET"])
@token_required
def me():
    from flask import g
    return jsonify({"success": True, "username": g.current_user})
