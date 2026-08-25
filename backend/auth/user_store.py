"""
User storage for the dashboard's login system.

Backed by a small SQLite database (no extra dependency needed - sqlite3 is
part of the Python standard library). Passwords are never stored in plain
text - only a salted werkzeug hash.

On first import, a default admin account is seeded IF the users table is
empty, so the dashboard is usable immediately after this feature is added.
Change the default password after first login (or just register a new
account and delete the default one via the DB).
"""

import sqlite3
import threading
from pathlib import Path

from werkzeug.security import generate_password_hash, check_password_hash

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "users.db"

DEFAULT_USERNAME = "admin"
DEFAULT_PASSWORD = "admin123"   # change this after first login

_lock = threading.Lock()


def _get_conn():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with _lock:
        conn = _get_conn()
        try:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.commit()

            existing = conn.execute("SELECT COUNT(*) AS c FROM users").fetchone()

            if existing["c"] == 0:
                conn.execute(
                    "INSERT INTO users (username, password_hash) VALUES (?, ?)",
                    (DEFAULT_USERNAME, generate_password_hash(DEFAULT_PASSWORD)),
                )
                conn.commit()
                print(
                    "[Auth] No users found - seeded default account "
                    f"'{DEFAULT_USERNAME}' / '{DEFAULT_PASSWORD}'. "
                    "Change this password or register a new account."
                )
        finally:
            conn.close()


def get_user(username):
    conn = _get_conn()
    try:
        row = conn.execute(
            "SELECT * FROM users WHERE username = ?",
            (username,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def create_user(username, password):
    username = (username or "").strip()

    if not username or not password:
        raise ValueError("username and password are required")

    if len(password) < 6:
        raise ValueError("password must be at least 6 characters")

    with _lock:
        conn = _get_conn()
        try:
            existing = conn.execute(
                "SELECT id FROM users WHERE username = ?",
                (username,),
            ).fetchone()

            if existing:
                raise ValueError("username already exists")

            conn.execute(
                "INSERT INTO users (username, password_hash) VALUES (?, ?)",
                (username, generate_password_hash(password)),
            )
            conn.commit()
        finally:
            conn.close()

    return {"username": username}


def verify_credentials(username, password):
    user = get_user((username or "").strip())

    if not user:
        return None

    if not check_password_hash(user["password_hash"], password or ""):
        return None

    return {"username": user["username"]}
