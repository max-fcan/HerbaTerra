# iNaturalist SQLite Database – Semantic & Technical Model

This document describes the schema used to store iNaturalist observations for scraping, along with the technical rationale and relationships.

## Objectives

- **Preserve raw API payloads** for traceability and reprocessing.
- **Normalize core entities** (observations, users, taxa, media, identifications).
- **Support efficient queries** for spatial, taxonomic, and quality filters.

## Tables (Semantic Meaning)

### `observations`
Represents one iNaturalist observation event.

Key fields:
- `id`: iNat observation ID (PK)
- `observed_on`, `created_at`, `updated_at`: time metadata
- `latitude`, `longitude`, `positional_accuracy`: spatial location and precision
- `quality_grade`, `geoprivacy`, `license`: data quality + sharing constraints
- `place_guess`, `species_guess`: user-provided guesses
- `taxon_id`, `user_id`: links to normalized taxa/users
- `raw_json`: full API payload for the observation

### `users`
Observer or identifier accounts.

Key fields:
- `id`: iNat user ID (PK)
- `login`, `name`
- `raw_json`

### `taxa`
Normalized taxonomic entities.

Key fields:
- `id`: iNat taxon ID (PK)
- `name`, `rank`, `iconic_taxon_name`, `ancestry`
- `raw_json`

### `photos`
Media objects attached to observations.

Key fields:
- `id`: iNat photo ID (PK)
- `url`, `license_code`
- `raw_json`

### `sounds`
Audio objects attached to observations.

Key fields:
- `id`: iNat sound ID (PK)
- `file_url`, `license_code`
- `raw_json`

### `identifications`
Community identifications for observations.

Key fields:
- `id`: iNat identification ID (PK)
- `observation_id`: FK to observations
- `user_id`, `taxon_id`: who identified what
- `is_current`: whether this is the current ID
- `created_at`
- `raw_json`

### `observation_photos`
Join table to preserve photo order.

Key fields:
- `observation_id`, `photo_id`
- `position`: order of photos in the observation

### `observation_sounds`
Join table for observation audio.

Key fields:
- `observation_id`, `sound_id`

## Relationships (Technical)

- `observations` → `users` (many observations per user)
- `observations` → `taxa` (many observations per taxon)
- `observations` → `photos` (many-to-many via `observation_photos`)
- `observations` → `sounds` (many-to-many via `observation_sounds`)
- `observations` → `identifications` (one-to-many)
- `identifications` → `users` / `taxa` (many-to-one)

Foreign keys enforce integrity; most child rows cascade on observation delete.

## Indexes

Indexes optimize common filtering:
- `idx_obs_coords` on `(latitude, longitude)` for spatial queries
- `idx_obs_taxon` on `taxon_id`
- `idx_obs_user` on `user_id`
- `idx_obs_quality` on `quality_grade`
- `idx_obs_photos_obs` on `observation_photos.observation_id`
- `idx_obs_sounds_obs` on `observation_sounds.observation_id`
- `idx_idents_obs` on `identifications.observation_id`
- `idx_idents_taxon` on `identifications.taxon_id`

## Storage Flow

1. **Fetch** observations from the API using typed params.
2. **Normalize** and upsert users/taxa/media.
3. **Persist** the observation and all related records.

## Files

- Storage layer: app/services/inaturalist_db.py
- Scraper orchestrator: app/services/inaturalist_store.py
