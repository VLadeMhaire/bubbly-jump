CREATE TABLE IF NOT EXISTS devices (
  id         TEXT PRIMARY KEY,
  first_seen INTEGER NOT NULL,
  last_seen  INTEGER NOT NULL,
  user_agent TEXT
);
CREATE TABLE IF NOT EXISTS events (
  id        INTEGER PRIMARY KEY AUTOINCREMENT,
  device_id TEXT NOT NULL REFERENCES devices(id),
  type      TEXT NOT NULL,
  score     INTEGER,
  ts        INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_events_device ON events(device_id, type);
CREATE INDEX IF NOT EXISTS idx_events_ts ON events(ts);
