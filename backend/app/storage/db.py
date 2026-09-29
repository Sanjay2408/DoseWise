"""
SQLite persistence layer for DoseWise.

Replaces the old single shared state.json. Each registered user gets their
own agent-state document (stored as a JSON blob) so data is fully isolated
per account. Uses only the Python standard library (sqlite3).
"""

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any, Optional

from app.config import DATA_DIR

_STORAGE_DIR = DATA_DIR
DB_PATH = _STORAGE_DIR / "dosewise.db"

# sqlite3 connections are cheap; a short-lived connection per operation with a
# module lock keeps writes safe across FastAPI's threadpool workers.
_write_lock = Lock()


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db() -> None:
    _STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    with _write_lock, _connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id            TEXT PRIMARY KEY,
                email         TEXT NOT NULL UNIQUE COLLATE NOCASE,
                name          TEXT NOT NULL DEFAULT '',
                password_hash TEXT NOT NULL,
                created_at    TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS user_state (
                user_id    TEXT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
                state_json TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            """
        )


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# --- Users ---

def create_user(email: str, name: str, password_hash: str) -> dict:
    """Insert a new user. Raises ValueError if the email is already registered."""
    user_id = uuid.uuid4().hex
    with _write_lock, _connect() as conn:
        try:
            conn.execute(
                "INSERT INTO users (id, email, name, password_hash, created_at) VALUES (?, ?, ?, ?, ?)",
                (user_id, email.strip().lower(), name.strip(), password_hash, _now_iso()),
            )
        except sqlite3.IntegrityError as e:
            raise ValueError("An account with this email already exists") from e
    return {"id": user_id, "email": email.strip().lower(), "name": name.strip()}


def get_user_by_email(email: str) -> Optional[dict]:
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE email = ?", (email.strip().lower(),)
        ).fetchone()
    return dict(row) if row else None


def get_user_by_id(user_id: str) -> Optional[dict]:
    with _connect() as conn:
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    return dict(row) if row else None


# --- Per-user agent state ---

def load_user_state(user_id: str) -> Optional[dict]:
    """Return the stored agent state for a user, or None if none saved yet."""
    with _connect() as conn:
        row = conn.execute(
            "SELECT state_json FROM user_state WHERE user_id = ?", (user_id,)
        ).fetchone()
    if row is None:
        return None
    try:
        data = json.loads(row["state_json"])
        return data if isinstance(data, dict) else None
    except (json.JSONDecodeError, TypeError):
        return None


def save_user_state(user_id: str, state: dict) -> None:
    payload = json.dumps(state, default=str)
    with _write_lock, _connect() as conn:
        conn.execute(
            """
            INSERT INTO user_state (user_id, state_json, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                state_json = excluded.state_json,
                updated_at = excluded.updated_at
            """,
            (user_id, payload, _now_iso()),
        )
