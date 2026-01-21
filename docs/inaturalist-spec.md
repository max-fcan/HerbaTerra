# iNaturalist Integration Spec

## Scope

This document describes how the iNaturalist integration works in this repository: API access, scraping orchestration, SQLite storage, and related logging and utilities. It is based on the current code in the `app/services` and `app/workers` modules.

## Modules

### API client

**File:** [app/services/inaturalist_api.py](../app/services/inaturalist_api.py)

**Purpose**

- Provide a typed wrapper around the iNaturalist observations endpoint.
- Normalize pagination headers so the caller can drive pagination.

**Endpoint**

- `GET https://inaturalist.org/observations.json`

**Request parameters**
The client exposes a typed `get_observation(...)` function that passes parameters through to the API. Key options include:

- Paging: `page`, `per_page`
- Sorting: `order_by`, `order`
- Filters: `q`, `taxon_id`, `taxon_name`, `iconic_taxa[]`, `has[]`, `quality_grade`
- Date filters: `on`, `year`, `month`, `day`, `d1`, `d2`, `m1`, `m2`, `h1`, `h2`
- Bounding box: `swlat`, `swlng`, `nelat`, `nelng`
- Licenses: `license`, `photo_license`
- Misc: `list_id`, `updated_since`, `extra`

**Validation**

- Parameter ranges are validated before the request (e.g., `per_page` must be 1–200, latitude/longitude ranges are enforced).

**Response**
The function returns a dict with:

- `results`: list of observations (raw iNaturalist JSON)
- `pagination`: normalized headers
  - `total_entries` from `X-Total-Entries`
  - `page` from `X-Page`
  - `per_page` from `X-Per-Page`

**Notes**

- If the API returns a list directly, it is accepted and normalized into `results`.
- Network calls use `requests.Session` when provided.
- Transient errors are retried with exponential backoff; retryable statuses default to 429/5xx and can be overridden.

---

### Scraper orchestration

**File:** [app/workers/inaturalist_store.py](../app/workers/inaturalist_store.py)

**Purpose**

- Fetch multiple pages of observations from iNaturalist and persist them to SQLite.

**Function**
`scraрe_observations_to_sqlite(...)` (see file for full signature)

**Behavior**

- Initializes a `requests.Session` and starts at `start_page` (default 1).
- Fetches pages until one of the following:
  - `max_pages` reached
  - empty results returned
  - a page returns fewer items than `per_page`
- Adds a delay between pages (`delay_seconds`, default 0.5 seconds).
- Persists pages using a single SQLite connection and commits in batches (`commit_every_pages` / `commit_every_observations`).
- Supports retry/backoff parameters passed through to the API client.
- Optional checkpointing writes `next_page`, `updated_since`, and counters to disk to allow resuming.

**Return value**
`ScrapeSummary` with:

- `pages_fetched`
- `observations_saved`
- `total_entries` (from headers)
- `last_page` (from headers)

**Logging**

- Logs to `logs/inaturalist_store.log` via `configure_logging`.

**Example use**
The module includes a `__main__` sample that scrapes plant observations with filters like `has=geo,photos` and license constraints.

---

### SQLite storage

**File:** [app/services/inaturalist_db.py](../app/services/inaturalist_db.py)

**Purpose**

- Normalize observation JSON into relational tables.
- Preserve the full raw JSON for each entity to keep data lossless.

**Schema**

- `users`: `id`, `login`, `name`, `raw_json` (compressed BLOB)
- `taxa`: `id`, `name`, `rank`, `iconic_taxon_name`, `ancestry`, `raw_json` (compressed BLOB)
- `observations`: core observation fields + `taxon_id`, `user_id`, `raw_json` (compressed BLOB)
- `photos`: `id`, `url`, `license_code`, `raw_json` (compressed BLOB)
- `observation_photos`: join table with `position`
- `sounds`: `id`, `file_url`, `license_code`, `raw_json` (compressed BLOB)
- `observation_sounds`: join table
- `identifications`: `id`, `observation_id`, `user_id`, `taxon_id`, `is_current`, `created_at`, `raw_json` (compressed BLOB)
- `location_tags`: `observation_id`, `city`, `admin1`, `admin2`, `country`, `continent`, `error`

**Indexes**
Indexes exist for common access patterns:

- `observations`: coordinates, taxon, user, quality grade
- `observation_photos`: observation id
- `observation_sounds`: observation id
- `identifications`: observation id, taxon
- `location_tags`: country, continent

**Data compression**

- All `raw_json` fields are stored as compressed BLOBs using zlib (level 6), reducing DB size by ~50-70% and improving I/O performance.

**Normalization details**

- **Coordinates**: `latitude`/`longitude` are parsed to float. If missing/invalid, falls back to `geojson.coordinates`.
- **Users & taxa**: upserted from embedded `user`/`taxon` objects and referenced by `user_id` and `taxon_id` (nullable). If the embedded objects are missing, the foreign keys remain `NULL` (no fallback to `user_id`/`taxon_id` scalar fields).
- **Photos**: URL normalization prefers original size by converting `square_url` to `original` when possible, otherwise falls back to largest available size.
- **Identifications**: each identification is upserted, with `is_current` derived from `current`. Identifications are only present when the API request includes `extra=identifications` (default in the scraper is currently set to request them). Useful for tracking community consensus, expert opinions, and observation quality evolution over time.
- **Location tags**: reverse geocoded separately via `enrich_observations_with_location_tags()`, using the location tagging worker to add city/country/continent metadata.

**Persistence flow**

- `init_db(db_path)` sets up the schema.
- `save_inat_response(db_path, response_json)` extracts `results` and delegates to `save_observations(...)`.
- `save_observations(...)` can reuse an existing connection and optionally defer commits for bulk loads.

**Logging**

- Logs to `logs/inaturalist_db.log` via `configure_logging`.

**SQLite pragmas**

- Connections enable `WAL` journal mode and `synchronous=NORMAL` to improve bulk-write performance.

---

## Location enrichment

**Purpose**

- Add reverse-geocoded location metadata (city, admin regions, country, continent) to observations with coordinates.

**Function**
`enrich_observations_with_location_tags(db_path, *, connection=None, batch_size=1000, skip_existing=True)`

**Behavior**

- Queries observations with coordinates but no location tags (when `skip_existing=True`).
- Batch reverse geocodes using the `LocationTagger` from [app/workers/location_tags.py](../app/workers/location_tags.py).
- Groups identical coordinates so reverse geocoding is done once per unique coordinate, then inserts tags for all observations at that coordinate.
- Inserts results into the `location_tags` table, with one row per observation.
- Processes in batches to handle large datasets efficiently.

**Integration points**

- Can be called after scraping completes, or as a separate enrichment step.
- Reuses the same DB connection for efficient batch processing.
- Errors (out of bounds, invalid coords, not found) are recorded in the `error` field.

**Example use**

```python
from app.services.inaturalist_db import enrich_observations_with_location_tags

# Enrich all observations that don't have location tags yet
tagged_count = enrich_observations_with_location_tags(
    "temp/inat_test.db",
    batch_size=1000,
    skip_existing=True,
)
print(f"Tagged {tagged_count} observations")
```

---

### Location tagging (supporting utility)

**File:** [app/workers/location_tags.py](../app/workers/location_tags.py)

**Purpose**

- Reverse geocode coordinates to city/admin/country and enrich with continent names.
- This utility is separate from the iNaturalist scraper but is used for location enrichment in the project.

**Behavior**

- Uses `reverse_geocoder` and a static ISO3166 CSV mapping.
- Validates coordinates and returns structured `LocationTags` with error flags such as `OOB` or `Invalid`.

**Data dependencies**

- [app/static/data/iso3166_country_codes_continents.csv](../app/static/data/iso3166_country_codes_continents.csv)
- [app/static/data/iso3166_country_codes_continents_modified.csv](../app/static/data/iso3166_country_codes_continents_modified.csv)

---

## Operational notes

### Rate limiting & politeness

- The scraper enforces a delay between page requests (`delay_seconds`), default 0.5 seconds.
- The iNaturalist API limits may change; tune `delay_seconds` and `per_page` accordingly.

### Data integrity

- All entities store `raw_json` to preserve fields not explicitly mapped in SQL.
- Foreign keys are enabled (`PRAGMA foreign_keys = ON`) with delete behavior defined per table.

### Configuration

- Database path is provided by the caller. Common path in this repo is `temp/*.db` for local runs.

---

## Usage summary

1. Call `scrape_observations_to_sqlite(...)` with your filters.
2. The scraper fetches pages via `get_observation(...)` and writes to SQLite.
3. SQLite tables are created automatically on first run.

---

## Known limitations

- The scraper currently only targets the observations endpoint.
- There is no deduplication across runs beyond SQLite upsert semantics (same IDs are replaced).
- No CLI wrapper is provided; invocation is via Python modules or custom scripts.
