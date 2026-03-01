# HerbaTerra

HerbaTerra is a Flask web app for exploring and playing with global plant occurrence data.
It combines:
- an interactive country map hub,
- a filterable plant catalogue,
- a GeoGuessr-style play mode with map-based guesses,
- and an embedded local SQLite replica synced from Turso on startup.

## Stack

- Python 3
- Flask
- libsql / libsql-client (embedded replica sync from Turso)
- SQLite (local replica queries)
- Bootstrap 5 (layout)
- Leaflet + OpenStreetMap tiles (interactive maps)
- Three.js (landing page Earth background)

## Main Features

- Startup replica bootstrap:
  - On app start, a background thread syncs a local database replica.
  - Until ready, protected routes are gated and users are redirected to `/start`.
- Hub map (`/hub`):
  - Country GeoJSON map with popups linking directly to scoped Play and Catalogue views.
- Catalogue (`/catalogue`):
  - Search by species/common name/family/genus.
  - Filter by country and continent.
  - Sort by popularity, image count, or alphabetical order.
  - Species detail pages with location chips, map stats, and paginated image API loading.
- Play mode (`/play`):
  - Scope by world, continent, or country.
  - Timer-based guessing with reveal and score computation.
  - Session-backed multi-round state.
- Operational endpoints:
  - `/health`
  - `/api/db/replica-status`

## Route Overview

### Pages

- `/` landing page
- `/start` replica loading page (polls status API)
- `/hub` interactive map hub
- `/play` play screen
- `/catalogue` species catalogue
- `/catalogue/species/<species_name>` species detail
- `/about` placeholder page (currently empty)

### API

- `GET /api/db/replica-status` current bootstrap state
- `GET /api/catalogue/filter-options`
- `GET /api/catalogue/species/<species_name>/images`
- `GET /api/catalogue/species/<species_name>/map-stats`
- `POST /play/guess`
- `POST /play/score`

## Project Structure

```text
.
|- app/
|  |- __init__.py             # Flask app factory + route gate until replica is ready
|  |- config.py               # Env-driven config
|  |- logging_setup.py        # Console + rotating file logging
|  |- db/
|  |  |- __init__.py          # Bootstrap thread orchestration
|  |  |- bootstrap.py         # Embedded replica sync logic
|  |  |- connections.py       # SQLite connection helpers + readiness status
|  |- routes/                 # Blueprints (pages, play, catalogue, api, geojson, health)
|  |- services/               # Domain logic (catalogue, play, geocoding)
|  |- templates/              # Jinja templates
|  |- static/                 # CSS, JS, Earth textures
|- data/
|  |- countries_*.geojson
|  |- iso3166_country_codes_continents_modified.csv
|  |- sql/                    # Optional index optimization scripts
|- docs/
|- logs/
|- run.py                     # Local run entrypoint
|- requirements.txt
```

## Quick Start

### 1) Create and activate a virtual environment

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

macOS/Linux:

```bash
python -m venv .venv
source .venv/bin/activate
```

### 2) Install dependencies

```bash
pip install -r requirements.txt
```

### 3) Configure environment

The app loads `.env.production` by default (see `app/config.py`).

Minimum required variables for replica sync in the current code:

```env
TURSO100_DATABASE_URL=libsql://...
TURSO100_AUTH_TOKEN=...
```

Notes:
- `bootstrap.py` also checks `TURSO_DATABASE_URL` and `TURSO_AUTH_TOKEN`, but these keys are not currently defined in `Config`.
- `TURSO500_DATABASE_URL` and `TURSO500_AUTH_TOKEN` are defined in `Config` but not currently used by bootstrap.

Optional app settings:

```env
PORT=5000
FLASK_DEBUG=false
SECRET_KEY=change-me
LOCAL_DB_PATH=data/plants.db
MAP_GEOJSON_RESOLUTION=medium
PLAY_ROUNDS=4
PLAY_GUESS_SECONDS=30
PLAY_REVEAL_AFTER_SUBMIT=true
PLAY_WORLD_ANTARCTICA_PROBABILITY=0.05
LOG_LEVEL=INFO
```

### 4) Run

```bash
python run.py
```

Then open:

- `http://127.0.0.1:5000/` (or your configured port)

First run can take time while the local replica syncs.

## Replica Bootstrap Behavior

- `init_db()` starts a daemon thread for bootstrap.
- Replica states include: `idle`, `starting`, `syncing`, `ready`, `already_exists`, `error`.
- Until state is `ready` or `already_exists`:
  - page routes (except `/`, `/start`) redirect to `/start`,
  - API routes return `503` with status payload.

This protects the local DB from being queried before sync completion.

## Data and Assets

- GeoJSON files are served from `/geojson/<filename>` with an allowlist from config.
- Country and continent lookups come from:
  - `data/iso3166_country_codes_continents_modified.csv`
- SQL index scripts are provided in:
  - `data/sql/index_optimization.sql`
  - `data/sql/index_optimization_small.sql`

## Logging

- Configured in `app/logging_setup.py`.
- Outputs:
  - console,
  - rotating file log (default `logs/app.log`, 1 MB max, 3 backups).

Format:

```text
%(asctime)s | %(levelname)s | %(name)s:%(lineno)d | %(message)s
```

## Troubleshooting

- App stuck on loading page:
  - check `GET /api/db/replica-status`,
  - verify Turso URL/token in `.env.production`,
  - ensure network access for first sync.
- `libsql is not installed`:
  - run `pip install -r requirements.txt`.
- Map not showing:
  - verify GeoJSON files exist in `data/`,
  - check browser console for Leaflet asset loading failures.
- Port conflict:
  - set a different `PORT` value.

## Current Gaps

- No automated test suite is included yet.
- `/about` is currently a placeholder template.
