# Bubbly Jump + play tracker

- `index.html`  the game (tracks visits, plays and game-overs per device)
- `stats.html`  dashboard: devices, plays per device, plays per day
- `main.py`     FastAPI backend, SQLite file `plays.db` (created on first run)

## Run

    pip install -r requirements.txt
    uvicorn main:app --host 0.0.0.0 --port 8000

Game: http://localhost:8000/   Stats: http://localhost:8000/stats.html

Each browser gets a random anonymous id stored in localStorage, so "device" means
one browser profile. Clearing site data or using a private window counts as a new device.

## Optional

- `STATS_TOKEN=secret uvicorn main:app ...` protects the stats API; open `/stats.html?token=secret`.
- `DB_PATH=/data/plays.db` changes where the database is stored.

The game must be opened through the server (not as a file) for tracking to work.
