"""
Persistence layer.

- Live operational state (hospitals/shelters/resources/volunteers) is kept
  in-memory in `STATE`, mutated as each simulation runs, mirroring how the
  brief describes Redis holding "live resource availability".
- Past incidents + their full situation reports are persisted to a local
  SQLite database (`rescuenet.db`), mirroring the brief's "Long-Term Memory"
  / PostgreSQL role, so the dashboard can show history across restarts.
"""
import sqlite3
import json
import os
from datetime import datetime, timezone

from backend.data.simulated_data import default_state

DB_PATH = os.path.join(os.path.dirname(__file__), "rescuenet.db")

STATE = default_state()


def reset_state():
    global STATE
    STATE = default_state()
    return STATE


def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS incidents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            disaster_type TEXT NOT NULL,
            location_name TEXT NOT NULL,
            report_json TEXT NOT NULL
        )
        """
    )
    conn.commit()
    conn.close()


def save_incident(disaster_type: str, location_name: str, report: dict) -> int:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.execute(
        "INSERT INTO incidents (created_at, disaster_type, location_name, report_json) VALUES (?, ?, ?, ?)",
        (datetime.now(timezone.utc).isoformat(), disaster_type, location_name, json.dumps(report)),
    )
    conn.commit()
    incident_id = cur.lastrowid
    conn.close()
    return incident_id


def list_incidents(limit: int = 20):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT id, created_at, disaster_type, location_name FROM incidents ORDER BY id DESC LIMIT ?",
        (limit,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_incident(incident_id: int):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT * FROM incidents WHERE id = ?", (incident_id,)).fetchone()
    conn.close()
    if not row:
        return None
    d = dict(row)
    d["report"] = json.loads(d.pop("report_json"))
    return d
