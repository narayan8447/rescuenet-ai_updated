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
import threading
from datetime import datetime, timezone

from backend.simulation.engine import SimulationEngine

DB_PATH = os.path.join(os.path.dirname(__file__), "rescuenet.db")

_sim_engine = SimulationEngine()
STATE = _sim_engine.get_state()

# Thread-safe Singleton SQLite Connection
_db_lock = threading.Lock()
_conn = None

def get_db_connection():
    global _conn
    if _conn is None:
        _conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        _conn.row_factory = sqlite3.Row
    return _conn

def reset_state():
    global _sim_engine, STATE
    _sim_engine = SimulationEngine()
    STATE = _sim_engine.get_state()
    return STATE

def advance_simulation(ticks: int = 1):
    global _sim_engine, STATE
    _sim_engine.step(ticks)
    STATE = _sim_engine.get_state()
    return STATE

def init_db():
    with _db_lock:
        conn = get_db_connection()
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

def save_incident(disaster_type: str, location_name: str, report: dict) -> int:
    with _db_lock:
        conn = get_db_connection()
        cur = conn.execute(
            "INSERT INTO incidents (created_at, disaster_type, location_name, report_json) VALUES (?, ?, ?, ?)",
            (datetime.now(timezone.utc).isoformat(), disaster_type, location_name, json.dumps(report)),
        )
        conn.commit()
        return cur.lastrowid

def list_incidents(limit: int = 20):
    with _db_lock:
        conn = get_db_connection()
        rows = conn.execute(
            "SELECT id, created_at, disaster_type, location_name FROM incidents ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]

def get_incident(incident_id: int):
    with _db_lock:
        conn = get_db_connection()
        row = conn.execute("SELECT * FROM incidents WHERE id = ?", (incident_id,)).fetchone()
        if not row:
            return None
        d = dict(row)
        d["report"] = json.loads(d.pop("report_json"))
        return d
