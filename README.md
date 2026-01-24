# HerbaTerra

Flask-powered playground for herb/geo themed pages with animated Earth/gradient backgrounds, reusable logging/configuration helpers, and data/utility scripts for geo tagging and reverse geocoding.

---

## What’s here

- Flask app in app/ with routes for **Home**, **About**, **Play**, **Quiz**, and **Profile**, rendering Jinja templates with shared layout and partials.
- Backgrounds: 3D Earth (Three.js) and SVG “gooey” gradient; pages select a background via template includes.
- Logging helpers in app/logging_config.py used by the app factory to set up console + rotating file logs with parent_file:lineno formatting.
- Mapillary client in app/services/mapillary_client.py for Graph API calls (requires a token).
- Location tag utilities in app/services/location_tags.py and reverse-geocoding tooling in app/workers/\_reverse_geocoding/.
- Static data in app/static/data/: ISO3166 country/continent mappings plus modifications notes.
- Data assets in data/: a DuckDB dataset plus GBIF metadata/citation files.

---

## Project layout

```
.
├── README.md
├── requirements.txt
├── run.py                                  # Dev entry point
├── config/
│   └── config.py                           # Env-driven Flask config (logging, secrets, tokens, DB path)
├── app/
│   ├── __init__.py                         # create_app + logging bootstrap
│   ├── logging_config.py                   # configure_logging/configure_app_logging helpers
│   ├── routes/
│   │   ├── main.py                         # home/about landing routes
│   │   ├── play.py                         # /play pages
│   │   ├── quiz.py                         # /quiz pages
│   │   └── profile.py                      # /profile pages
│   ├── services/
│   │   ├── location_tags.py                # location/country/continent helpers
│   │   └── mapillary_client.py             # Mapillary Graph API wrapper
│   ├── static/
│   │   ├── css/
│   │   │   ├── gradient.css
│   │   │   └── style.css
│   │   ├── data/
│   │   │   ├── iso3166_country_codes_continents.csv
│   │   │   ├── iso3166_country_codes_continents_modified.csv
│   │   │   └── modifications.md
│   │   ├── img/
│   │   │   ├── earth/
│   │   │   │   └── stars/
│   │   │   └── logos/
│   │   │       ├── main/
│   │   │       └── mountain/
│   │   └── js/
│   │       ├── earth.js
│   │       ├── gradient.js
│   │       ├── main.js
│   │       └── vendor/
│   │           └── three/
│   │               ├── OrbitControls.js
│   │               └── three.module.js
│   ├── templates/
│   │   ├── base.html
│   │   ├── about.html
│   │   ├── index.html
│   │   ├── partials/
│   │   │   ├── earth.html
│   │   │   └── gradient.html
│   │   ├── play/
│   │   │   ├── daily.html
│   │   │   ├── game.html
│   │   │   ├── index.html
│   │   │   ├── map.html
│   │   │   └── tournaments.html
│   │   ├── profile/
│   │   │   ├── index.html
│   │   │   ├── settings.html
│   │   │   └── statistics.html
│   │   └── quiz/
│   │       ├── catalogue.html
│   │       ├── index.html
│   │       └── play.html
│   └── workers/
│       └── _reverse_geocoding/
│           ├── benchmark_rg.py
│           └── rg_duckdb.py
├── data/
│   ├── gbif_plants.duckdb                   # DuckDB dataset
│   ├── citations.txt
│   ├── rights.txt
│   ├── meta.xml
│   ├── metadata.xml
│   └── dataset/
│       └── 50c9509d-22c7-4a22-a47d-8c48425ef4a7.xml
├── docs/
│   └── inaturalist-spec.md
├── logs/                                    # log output (app.log, workers.log)
└── temp/
    └── test_db.py
```

---

## Getting started

1. Clone and enter the repo  
   `git clone <your-repo-url> && cd HerbaTerra`

2. Create and activate a venv  
   `python -m venv .venv && source .venv/bin/activate` (Windows: `\.\.venv\Scripts\activate`)

3. Install deps  
   `pip install -r requirements.txt`

4. Run the dev server

- With Flask: `FLASK_APP=run.py FLASK_ENV=development flask run`
- Or directly: `python run.py` (binds to 0.0.0.0, port from $PORT or 5000)

Open http://127.0.0.1:5000/ to see the UI.

---

## Configuration

config/config.py reads environment variables:

- SECRET_KEY (session signing; default dev key)
- APP_DB_PATH / APP_DB (Flask DB path, default instance/app.db)
- Mapillary token: MAPILLARY_ACCESS_TOKEN / MAPILLARY_TOKEN / MPY_ACCESS_TOKEN
- Logging: LOG_LEVEL, LOG_FORMAT, LOG_DIR, LOG_FILE, LOG_MAX_BYTES, LOG_BACKUP_COUNT
- Flask: FLASK_APP, FLASK_ENV, PORT

These can be set in your shell or a .env file.

---

## Logging

- create_app calls configure_app_logging, which wires console + rotating file handlers (default logs/app.log).
- Default format: %(asctime)s | %(levelname)-7s | %(parent_file)s:%(lineno)-3d | %(message)s
- Worker helpers can self-configure to logs/workers.log if no logging is set up yet.

---

## Frontend notes

- Layout: templates/base.html with navigation + footer; content blocks per route.
- Backgrounds: partials/earth.html (Three.js globe via static/js/earth.js) and partials/gradient.html (gooey gradient via static/js/gradient.js + CSS).
- Styles live in static/css/style.css and static/css/gradient.css; Earth assets under static/img/earth/.

---

## Services and workers

- app/services/mapillary_client.py: Requests-based Graph API wrapper with retry/backoff; requires a Mapillary token in env or Flask config.
- app/services/location_tags.py: Location tagging utilities; uses ISO3166 country/continent mapping in app/static/data/.
- app/workers/\_reverse_geocoding/rg_duckdb.py: Reverse geocoding against the DuckDB dataset; benchmark_rg.py provides benchmarking utilities.

---

## Data files

- app/static/data/iso3166_country_codes_continents.csv and iso3166_country_codes_continents_modified.csv: two-letter country code → continent mapping used by location tagging.
- app/static/data/modifications.md: notes about adjustments to the mapping file.
- data/gbif_plants.duckdb: DuckDB dataset for local queries.
- data/meta.xml, data/metadata.xml, data/dataset/\*.xml: GBIF metadata files.
- data/citations.txt and data/rights.txt: attribution and rights notes.

---

## Testing

No automated tests are included yet. pytest is in requirements.txt for future coverage. Use python -m py_compile <file.py> as a quick syntax check.

---

## Specs

See the integration spec: [docs/inaturalist-spec.md](docs/inaturalist-spec.md).
