"""SQLite-backed persistence for the estimate history.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from app import config


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Create the estimates table if it does not exist yet (idempotent)."""
    Path(config.DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = _connect()
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS estimates (
                id          TEXT PRIMARY KEY,
                inputs      TEXT NOT NULL,
                prediction  REAL NOT NULL,
                created_at  TEXT NOT NULL
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


def save(inputs: dict, prediction: float) -> dict:
    """Persist one estimate and return it as a record dict."""
    return save_many([(inputs, prediction)])[0]


def save_many(rows: list[tuple[dict, float]]) -> list[dict]:
    """Persist multiple estimates in a single transaction; return the records.
    """
    records = [
        {
            "id": str(uuid4()),
            "inputs": inputs,
            "prediction": prediction,
            "created_at": _now(),
        }
        for inputs, prediction in rows
    ]
    conn = _connect()
    try:
        conn.executemany(
            "INSERT INTO estimates (id, inputs, prediction, created_at) "
            "VALUES (?, ?, ?, ?)",
            [
                (r["id"], json.dumps(r["inputs"]), r["prediction"], r["created_at"])
                for r in records
            ],
        )
        conn.commit()
    finally:
        conn.close()
    return records


def list_all(limit: int = 100) -> list[dict]:
    """Return the most recent estimates, newest first."""
    conn = _connect()
    try:
        rows = conn.execute(
            "SELECT id, inputs, prediction, created_at "
            "FROM estimates ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    finally:
        conn.close()
    return [_row_to_record(r) for r in rows]


def get_one(estimate_id: str) -> dict | None:
    """Return a single estimate by id, or ``None`` if it does not exist."""
    conn = _connect()
    try:
        row = conn.execute(
            "SELECT id, inputs, prediction, created_at "
            "FROM estimates WHERE id = ?",
            (estimate_id,),
        ).fetchone()
    finally:
        conn.close()
    return _row_to_record(row) if row else None


def delete_one(estimate_id: str) -> bool:
    """Delete one estimate; return ``True`` if a row was actually removed."""
    conn = _connect()
    try:
        cur = conn.execute("DELETE FROM estimates WHERE id = ?", (estimate_id,))
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def _row_to_record(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "inputs": json.loads(row["inputs"]),
        "prediction": row["prediction"],
        "created_at": row["created_at"],
    }
