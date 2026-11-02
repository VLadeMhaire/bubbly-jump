"""Bubbly Jump backend: serves the game and records plays per device in SQLite.

Run:  uvicorn main:app --host 0.0.0.0 --port 8000
Env:  DB_PATH      sqlite file location (default: ./plays.db)
      STATS_TOKEN  if set, /api/stats requires ?token=... (the stats page forwards it)
"""
import os
import sqlite3
import time
from contextlib import closing
from pathlib import Path
from typing import Literal, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

BASE = Path(__file__).parent
DB_PATH = os.environ.get("DB_PATH", str(BASE / "plays.db"))
STATS_TOKEN = os.environ.get("STATS_TOKEN")

app = FastAPI(title="Bubbly Jump backend")


def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with closing(db()) as c:
        c.executescript(
            """
            CREATE TABLE IF NOT EXISTS devices (
                id         TEXT PRIMARY KEY,
                first_seen INTEGER NOT NULL,
                last_seen  INTEGER NOT NULL,
                user_agent TEXT
            );
            CREATE TABLE IF NOT EXISTS events (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id TEXT NOT NULL REFERENCES devices(id),
                type      TEXT NOT NULL,          -- visit | play | over
                score     INTEGER,
                ts        INTEGER NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_events_device ON events(device_id, type);
            CREATE INDEX IF NOT EXISTS idx_events_ts ON events(ts);
            """
        )
        c.commit()


init_db()


class Event(BaseModel):
    device_id: str = Field(min_length=8, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")
    type: Literal["visit", "play", "over"]
    score: Optional[int] = Field(default=None, ge=0, le=10_000_000)


@app.post("/api/event", status_code=204)
def record_event(ev: Event, request: Request):
    now = int(time.time())
    ua = (request.headers.get("user-agent") or "")[:300]
    with closing(db()) as c:
        c.execute(
            """INSERT INTO devices (id, first_seen, last_seen, user_agent) VALUES (?,?,?,?)
               ON CONFLICT(id) DO UPDATE SET last_seen=excluded.last_seen, user_agent=excluded.user_agent""",
            (ev.device_id, now, now, ua),
        )
        c.execute(
            "INSERT INTO events (device_id, type, score, ts) VALUES (?,?,?,?)",
            (ev.device_id, ev.type, ev.score, now),
        )
        c.commit()


@app.get("/api/stats")
def stats(token: Optional[str] = None):
    if STATS_TOKEN and token != STATS_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid token")
    with closing(db()) as c:
        devices = [
            dict(r)
            for r in c.execute(
                """SELECT d.id, d.user_agent, d.first_seen, d.last_seen,
                          SUM(e.type='visit') AS visits,
                          SUM(e.type='play')  AS plays,
                          MAX(CASE WHEN e.type='over' THEN e.score END) AS best_score,
                          MAX(CASE WHEN e.type='play' THEN e.ts END)    AS last_played
                   FROM devices d LEFT JOIN events e ON e.device_id = d.id
                   GROUP BY d.id ORDER BY plays DESC, d.last_seen DESC"""
            )
        ]
        total_plays = sum(d["plays"] or 0 for d in devices)
        since = int(time.time()) - 14 * 86400
        daily = [
            dict(r)
            for r in c.execute(
                """SELECT date(ts,'unixepoch') AS day,
                          SUM(type='play') AS plays,
                          COUNT(DISTINCT CASE WHEN type='play' THEN device_id END) AS devices
                   FROM events WHERE ts >= ? GROUP BY day ORDER BY day""",
                (since,),
            )
        ]
    return {
        "total_devices": len(devices),
        "devices_who_played": sum(1 for d in devices if d["plays"]),
        "total_plays": total_plays,
        "devices": devices,
        "daily": daily,
    }


@app.get("/")
def index():
    return FileResponse(BASE / "index.html")


@app.get("/stats.html")
def stats_page():
    return FileResponse(BASE / "stats.html")
