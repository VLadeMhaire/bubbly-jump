CREATE TABLE IF NOT EXISTS devices (
    id TEXT PRIMARY KEY,
    first_seen INTEGER NOT NULL,
    last_seen INTEGER NOT NULL,
    user_agent TEXT
);

CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id TEXT NOT NULL,
    type TEXT NOT NULL CHECK (type IN ('visit', 'play', 'over')),
    score INTEGER,
    ts INTEGER NOT NULL,
    FOREIGN KEY (device_id) REFERENCES devices(id)
);

CREATE INDEX IF NOT EXISTS idx_events_device_id
ON events(device_id);

CREATE INDEX IF NOT EXISTS idx_events_ts
ON events(ts);
