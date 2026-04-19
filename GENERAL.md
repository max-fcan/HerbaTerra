# HerbaTerra

HerbaTerra is a Flask application for exploring global plant occurrence data through maps, catalogue views, and a location-guessing game. The app boots from a local SQLite replica that is synchronized from Turso, so that runtime queries stay local once sync completes, on startup.

## Features

- An interactive map enabling users to explore and play with plants limited to a certain geographical region.
- A plant catalogue with search, taxonomy filters, geographic filters, and "sort by" options.
- Detail "species" pages that include a distribution heatmap and an image gallery.
- A timed play mode with world, continent, and country scopes.

## Stack

| Layer | Technology |
| --- | --- |
| Backend | Python 3, Flask |
| Database | Turso, libsql, SQLite |
| Frontend | Jinja2 templates, Bootstrap 5, custom CSS |
| Mapping | Leaflet, OpenStreetMap tiles, GeoJSON |
| 3D landing page | Three.js |

## Running locally

### 1. Create the virtual environment

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

macOS or Linux:

```bash
python -m venv .venv
source .venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment variables

Create a `.env.production` file in the project root. `app/config.py` loads this file automatically for the default runtime.

Required values:

| Variable | Description |
| --- | --- |
| `TURSO100_DATABASE_URL` | Turso database URL |
| `TURSO100_AUTH_TOKEN` | Turso auth token |

Common optional values:

| Variable | Default | Description |
| --- | --- | --- |
| `SECRET_KEY` | `super-secret-key` | Flask session secret |
| `PORT` | `5000` | HTTP port |
| `FLASK_DEBUG` | `false` | Enables debug mode |
| `DATA_DIR` | `data/` | Project data directory |
| `LOCAL_DB_PATH` | `temp/plants.db` | Path to the local SQLite replica |
| `MAP_GEOJSON_RESOLUTION` | `medium` | `low` or `medium` |
| `PLAY_ROUNDS` | `4` | Number of rounds in play mode |
| `PLAY_GUESS_SECONDS` | `60` | Seconds allowed per round |
| `PLAY_REVEAL_AFTER_SUBMIT` | `true` | Show the correct location after each round |
| `PLAY_WORLD_ANTARCTICA_PROBABILITY` | `0.05` | Chance of Antarctica in world scope |
| `LOG_LEVEL` | `INFO` | Application log level |
| `LOG_DIR` | `logs/` | Directory for log files |
| `LOG_FILE` | `logs/app.log` | Log file path |

### 4. Start the app

Use the project virtual environment:

```powershell
.\.venv\Scripts\python.exe run.py
```

Open `http://127.0.0.1:5000/` unless `PORT` overrides it.

The first launch can take a moment because the local replica is synchronized before the full app becomes available.

## Main routes

### Pages

| Route | Purpose |
| --- | --- |
| `GET /` | Landing page with the animated Earth background |
| `GET /start` | Replica loading screen |
| `GET /hub` | Interactive map hub |
| `GET /catalogue` | Catalogue list page |
| `GET /catalogue/species/<species_name>` | Species detail page |
| `GET /play` | Play mode |
| `POST /play/submit` | Submit or reveal the current round |
| `GET /about` | About page |

### API

| Route | Purpose |
| --- | --- |
| `GET /api/db/replica-status` | Replica bootstrap status |
| `GET /api/catalogue/filter-options` | Catalogue filter metadata |
| `GET /api/catalogue/species/<species_name>/images` | Cursor-based species image feed |
| `GET /api/catalogue/species/<species_name>/map-stats` | Per-country occurrence and image stats |

### Utility

| Route | Purpose |
| --- | --- |
| `GET /geojson/<filename>` | Serves allowlisted GeoJSON files |
| `GET /health` | Liveness probe |

## Replica bootstrap flow

`init_db()` starts a background sync that prepares the local replica. Until the replica is ready:

- `/start` stays available and polls the status API
- protected page routes redirect to the loading flow
- protected API routes return `503` with the replica status payload

Known bootstrap states:

| State | Meaning |
| --- | --- |
| `idle` | Bootstrap has not started yet |
| `starting` | Background thread launched |
| `syncing` | Replica is actively syncing |
| `ready` | Replica is usable |
| `already_exists` | Existing local replica was accepted |
| `error` | Bootstrap failed |

## Project layout

```text
.
|-- app/
|   |-- __init__.py              # Flask app factory and request gating
|   |-- config.py                # Environment-driven configuration
|   |-- logging_setup.py         # Console and rotating file logging
|   |-- db/
|   |   |-- __init__.py          # Bootstrap orchestration
|   |   |-- bootstrap.py         # Replica sync logic
|   |   `-- connections.py       # Local database access and status helpers
|   |-- routes/
|   |   |-- __init__.py          # Blueprint registration
|   |   |-- api.py               # JSON API endpoints
|   |   |-- catalogue.py         # Catalogue and species detail pages
|   |   |-- geojson.py           # GeoJSON file serving
|   |   |-- health.py            # Health check endpoint
|   |   |-- pages.py             # Public pages: landing, start, hub, about
|   |   `-- play.py              # Play mode pages and round submission
|   |-- services/
|   |   |-- catalogue.py         # Catalogue queries and species detail builders
|   |   |-- geocoding.py         # Country and continent lookup helpers
|   |   `-- play.py              # Round planning, scoring, image selection
|   |-- static/
|   |   |-- css/
|   |   |   |-- app.css          # Main shared stylesheet
|   |   |   `-- pages/
|   |   |       `-- about.css
|   |   |-- img/
|   |   `-- js/
|   `-- templates/
|       |-- partials/
|       |-- base.html
|       |-- index.html
|       |-- db_loading.html
|       |-- hub.html
|       |-- catalogue.html
|       |-- catalogue_species.html
|       |-- play.html
|       `-- about.html
|-- data/                        # GeoJSON, CSV, and SQL helper files
|   `-- country_areas.csv        # Country surface areas used for play scoring
|-- docs/
|-- logs/
|-- temp/                        # Local generated data such as the replica database
|-- run.py
`-- requirements.txt
```

## Data sources and assets

- Plant occurrence and media metadata come from GBIF-backed data in the project database.
- Country and continent mappings are read from `data/iso3166_country_codes_continents_modified.csv`.
- Country surface areas for play-mode scoring are read from `data/country_areas.csv`.
- GeoJSON boundary files are served from the `data/` directory according to the configured resolution.
- Landing page visuals use local Three.js assets stored under `app/static/`.
