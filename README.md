# HerbaTerra

Flask-powered playground for herb/geo themed pages with animated Earth/gradient backgrounds and reusable logging/configuration helpers.

---

## What’s here
- Flask app (`app/`) with routes for **Home**, **About**, **Play**, **Quiz**, and **Profile**; each renders simple Jinja templates backed by shared layout/partials.
- Backgrounds: 3D Earth (Three.js) and SVG “gooey” gradient, selectable per page via template variables.
- Logging helpers (`app/logging_config.py`) used by the app factory to set up console + rotating file logs with `parent_file:lineno` formatting.
- Mapillary client stub (`app/services/mapillary_client.py`) for Graph API calls (requires a token).
- Location tagging helper (`app/workers/location_tags.py`) using `reverse_geocoder` plus a country→continent CSV.
- Static data (`app/static/data/*`): ISO3166 country/continent mappings and a `modifications.md` note.

---

## Project layout
```
run.py                  # Dev entry point
config/config.py        # Env-driven Flask config (logging, secrets, tokens, DB path)
app/
  __init__.py           # create_app + logging bootstrap
  logging_config.py     # configure_logging/configure_app_logging helpers
  routes/               # main, play, quiz, profile blueprints
  templates/            # base layout, section pages, earth/gradient partials
  static/               # css, js (earth/gradient), images, data CSVs
  services/mapillary_client.py
  workers/location_tags.py
logs/                   # log output (app.log, workers.log)
requirements.txt
```

---

## Getting started
1) Clone and enter the repo  
`git clone <your-repo-url> && cd HerbaTerra`

2) Create and activate a venv  
`python -m venv .venv && source .venv/bin/activate` (Windows: `.\.venv\Scripts\activate`)

3) Install deps  
`pip install -r requirements.txt`

4) Run the dev server  
- With Flask: `FLASK_APP=run.py FLASK_ENV=development flask run`  
- Or directly: `python run.py` (binds to `0.0.0.0`, port from `$PORT` or 5000)

Open http://127.0.0.1:5000/ to see the UI.

---

## Configuration
`config/config.py` reads environment variables:
- `SECRET_KEY` (session signing; default dev key)
- `APP_DB_PATH` / `APP_DB` (Flask DB path, default `instance/app.db`)
- Mapillary token: `MAPILLARY_ACCESS_TOKEN` / `MAPILLARY_TOKEN` / `MPY_ACCESS_TOKEN`
- Logging: `LOG_LEVEL`, `LOG_FORMAT`, `LOG_DIR`, `LOG_FILE`, `LOG_MAX_BYTES`, `LOG_BACKUP_COUNT`
- Flask: `FLASK_APP`, `FLASK_ENV`, `PORT`

These can be set in your shell or a `.env` file.

---

## Logging
- `create_app` calls `configure_app_logging`, which wires console + rotating file handlers (default `logs/app.log`).
- Default format: `%(asctime)s | %(levelname)-7s | %(parent_file)s:%(lineno)-3d | %(message)s`
- The worker helper can self-configure to `logs/workers.log` if no logging is set up yet.

---

## Frontend notes
- Layout: `templates/base.html` with navigation + footer; content blocks per route.
- Backgrounds: `partials/earth.html` (Three.js globe via `static/js/earth.js`) and `partials/gradient.html` (gooey gradient via `static/js/gradient.js` + CSS).
- Styles live in `static/css/style.css` and `static/css/gradient.css`; Earth assets under `static/img/earth/`.

---

## Services and workers
- `app/services/mapillary_client.py`: Requests-based Graph API wrapper with retry/backoff; requires a Mapillary token in env or Flask config.
- iNaturalist pipeline: API client, scraper, and SQLite storage live in `app/services/inaturalist_api.py`, `app/services/inaturalist_store.py`, and `app/services/inaturalist_db.py`.
- `app/workers/location_tags.py`: Reverse geocoding via `reverse_geocoder`, enriches with continent from `app/static/data/iso3166_country_codes_continents*.csv`. Run a sample with `python -m app.workers.location_tags`.

---

## Data files
- `app/static/data/iso3166_country_codes_continents.csv` and `_modified.csv`: two-letter country code → continent mapping used by the worker.
- `app/static/data/modifications.md`: notes about adjustments to the mapping file.

---

## Testing
No automated tests are included yet. `pytest` is in `requirements.txt` for future coverage. Use `python -m py_compile <file.py>` as a quick syntax check.

---

## iNaturalist spec
See the detailed integration spec: [docs/inaturalist-spec.md](docs/inaturalist-spec.md).
