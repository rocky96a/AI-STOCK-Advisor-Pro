"""
Stateless auth tokens.

Uses itsdangerous (already a Flask dependency, no new install needed) to
sign a token containing the username. The token is opaque to the client -
they just store it and send it back as `Authorization: Bearer <token>`.

No server-side session table is needed for this to work; the signature
alone proves the token is valid and unexpired. Logout is handled client
side (drop the token) - see the note in auth/routes.py.
"""

import os
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired

# In production, set SECRET_KEY as an environment variable so tokens survive
# app restarts / multiple workers. Falls back to a per-process random key
# for local/dev use.
SECRET_KEY = os.environ.get("SECRET_KEY") or os.urandom(32).hex()

TOKEN_SALT = "joymaatara-auth-token"
TOKEN_MAX_AGE_SECONDS = 60 * 60 * 12  # 12 hours

_serializer = URLSafeTimedSerializer(SECRET_KEY, salt=TOKEN_SALT)


def generate_token(username):
    return _serializer.dumps({"username": username})


def verify_token(token):
    """Returns the payload dict if valid, otherwise None."""
    if not token:
        return None

    try:
        return _serializer.loads(token, max_age=TOKEN_MAX_AGE_SECONDS)
    except SignatureExpired:
        return None
    except BadSignature:
        return None
