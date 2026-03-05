# HerbaTerra

**HerbaTerra** is a Flask web application for exploring global plant occurrence data.  
It provides an interactive country hub map, a filterable species catalogue, and a GeoGuessr-style plant identification game — all backed by a local SQLite replica synced from a Turso cloud database at startup.

---

## Table of Contents

- [Stack](#stack)
- [Main Features](#main-features)
- [Project Structure](#project-structure)
- [Quick Start](#quick-start)
- [Environment Variables](#environment-variables)
- [Route Overview](#route-overview)
- [Replica Bootstrap Behavior](#replica-bootstrap-behavior)
- [Data and Assets](#data-and-assets)
- [Logging](#logging)
- [Troubleshooting](#troubleshooting)
- [Known Gaps](#known-gaps)

---

## Stack

| Layer | Technology |
|---|---|
| Backend | Python 3, Flask |
| Database | Turso (cloud) + libsql embedded replica → SQLite |
| Frontend layout | Bootstrap 5 |
| Maps | Leaflet + OpenStreetMap tiles |
| 3D landing page | Three.js |
| Config | python-dotenv |

---

## Main Features

### Startup Replica Bootstrap
On app start, a background thread syncs a local SQLite replica from Turso.  
Until sync completes, protected routes are gated and users are automatically redirected to `/start`, which polls the status API until the database is ready.

### Hub Map (`/hub`)
Interactive Leaflet choropleth map of the world. Each country opens a popup with direct links to scoped Play and Catalogue views for that country.

### Catalogue (`/catalogue`)
- Search by species name, common name, family, or genus.
- Filter by country and/or continent.
- Sort by popularity, image count, or alphabetical order.
- Species detail pages with:
  - occurrence location chips,
  - Leaflet map with per-country stats,
  - paginated image gallery loaded via API.

### Play Mode (`/play`)
- Scope by world, continent, or specific country.
- A plant photo is shown; the player guesses its location on a Leaflet map within a configurable timer.
- Score computed using a GeoGuessr-style formula (max 5 000 pts/round, based on Haversine distance).
- Reveal step shows the correct location after each guess.
- Multi-round sessions backed by Flask server-side session state.

### Operational Endpoints
- `GET /health` — liveness check.
- `GET /api/db/replica-status` — current bootstrap state.

---

## Project Structure

```text
.
├── app/
│   ├── __init__.py             # Flask app factory + route gate
│   ├── config.py               # Env-driven configuration
│   ├── logging_setup.py        # Console + rotating file logging
│   ├── db/
│   │   ├── __init__.py         # Bootstrap thread orchestration
│   │   ├── bootstrap.py        # Embedded replica sync logic
│   │   └── connections.py      # SQLite connection helpers + readiness status
│   ├── routes/                 # Blueprints
│   │   ├── api.py              # JSON API endpoints
│   │   ├── catalogue.py        # /catalogue routes
│   │   ├── geojson.py          # /geojson static file serving
│   │   ├── health.py           # /health liveness
│   │   ├── home.py             # / and /about
│   │   ├── pages.py            # /start loading page
│   │   └── play.py             # /play game routes
│   ├── services/               # Domain logic
│   │   ├── catalogue.py        # Catalogue queries and pagination
│   │   ├── geocoding.py        # Country/continent lookups from CSV
│   │   └── play.py             # Round planning, scoring, image selection
│   ├── templates/              # Jinja2 HTML templates
│   └── static/                 # CSS, JS, images, Three.js assets
├── data/
│   ├── countries_high_resolution.geojson
│   ├── countries_medium_resolution.geojson
│   ├── countries_low_resolution.geojson
│   ├── iso3166_country_codes_continents_modified.csv
│   └── sql/                    # Optional index optimization scripts
├── docs/                       # Project documentation
├── logs/                       # Runtime log files (auto-created)
├── run.py                      # Local development entrypoint
└── requirements.txt
```

---

## Quick Start

### 1. Create and activate a virtual environment

**Windows (PowerShell):**
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**macOS / Linux:**
```bash
python -m venv .venv
source .venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment

Create a `.env.production` file at the project root (loaded automatically by `app/config.py`).

See [Environment Variables](#environment-variables) for all available options.

### 4. Run

```bash
python run.py
```

Open `http://127.0.0.1:5000/` (or the configured port).  
The first run may take a moment while the local replica syncs from Turso.

---

## Environment Variables

### Required

| Variable | Description |
|---|---|
| `TURSO100_DATABASE_URL` | Turso database URL (`libsql://...`) |
| `TURSO100_AUTH_TOKEN` | Turso authentication token |

### Optional

| Variable | Default | Description |
|---|---|---|
| `SECRET_KEY` | `super-secret-key` | Flask session secret |
| `PORT` | `5000` | HTTP port |
| `FLASK_DEBUG` | `false` | Enable debug mode and auto-reloader |
| `LOCAL_DB_PATH` | `temp/plants.db` | Path to the local SQLite replica |
| `MAP_GEOJSON_RESOLUTION` | `medium` | GeoJSON resolution: `low`, `medium`, or `high` |
| `PLAY_ROUNDS` | `4` | Number of rounds per game |
| `PLAY_GUESS_SECONDS` | `30` | Timer per round (seconds) |
| `PLAY_REVEAL_AFTER_SUBMIT` | `true` | Show correct location after each guess |
| `PLAY_WORLD_ANTARCTICA_PROBABILITY` | `0.05` | Probability of an Antarctica round in world scope |
| `LOG_LEVEL` | `INFO` | Logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |
| `LOG_DIR` | `logs/` | Directory for log files |

---

## Route Overview

### Pages

| Route | Description |
|---|---|
| `GET /` | Landing page with animated Three.js Earth |
| `GET /start` | Replica loading page (polls status API) |
| `GET /hub` | Interactive country map hub |
| `GET /play` | Play game (accepts `country_code` / `continent_code` query params) |
| `GET /catalogue` | Species catalogue with filters |
| `GET /catalogue/species/<name>` | Species detail page |
| `GET /about` | About page |

### API

| Route | Description |
|---|---|
| `GET /api/db/replica-status` | Current bootstrap state |
| `GET /api/catalogue/filter-options` | Available filter values (countries, continents) |
| `GET /api/catalogue/species/<name>/images` | Paginated species images |
| `GET /api/catalogue/species/<name>/map-stats` | Per-country occurrence stats |
| `POST /play/guess` | Submit a map guess for the current round |
| `POST /play/score` | Finalise the round and compute the score |

### Utility

| Route | Description |
|---|---|
| `GET /health` | Liveness check |
| `GET /geojson/<filename>` | Serve a GeoJSON file (allowlisted) |

---

## Replica Bootstrap Behavior

`init_db()` starts a background daemon thread that syncs the Turso embedded replica.

**Bootstrap states:**

| State | Meaning |
|---|---|
| `idle` | Not yet started |
| `starting` | Thread launched |
| `syncing` | Actively syncing from Turso |
| `ready` | Sync complete — database is available |
| `already_exists` | Local replica already present and valid |
| `error` | Sync failed (check logs) |

**Route gating while not ready:**
- Page routes (except `/`, `/start`) → redirect to `/start`.
- API routes → `503` response with the status payload.

The `/start` page polls `GET /api/db/replica-status` and redirects to `/hub` once ready.

---

## Data and Assets

- **GeoJSON files** are served from `/geojson/<filename>` with a config-driven allowlist.
- **Country/continent mappings** are loaded from `data/iso3166_country_codes_continents_modified.csv`.
- **SQL index scripts** in `data/sql/` can be applied manually to optimize query performance on larger replicas:
  - `index_optimization.sql`
  - `index_optimization_small.sql`

---

## Logging

Configured in `app/logging_setup.py`. Outputs to both the console and a rotating file.

| Setting | Default |
|---|---|
| Log file | `logs/app.log` |
| Max file size | 1 MB |
| Backup count | 3 |

Log format:
```
%(asctime)s | %(levelname)s | %(name)s:%(lineno)d | %(message)s
```

---

## Troubleshooting

| Symptom | Action |
|---|---|
| App stuck on loading page | Check `GET /api/db/replica-status`; verify Turso URL/token in `.env.production`; ensure network access for first sync |
| `libsql is not installed` | Run `pip install -r requirements.txt` |
| Map not showing | Verify GeoJSON files exist in `data/`; check browser console for Leaflet errors |
| Port conflict | Set a different `PORT` value in `.env.production` |
| `403 / 404` on GeoJSON | Ensure `MAP_GEOJSON_RESOLUTION` is one of `low`, `medium`, `high` |

---

## Known Gaps

- No automated test suite.
