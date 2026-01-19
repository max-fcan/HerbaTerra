"""
SQLite storage layer for iNaturalist observations.

Normalizes iNaturalist JSON into relational tables and preserves raw JSON.
"""

from __future__ import annotations

import json
import logging
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator

from app.logging_config import configure_logging

LOGGER = configure_logging(
	level=logging.INFO,
	logger_name=__name__,
	log_filename="inaturalist_db.log",
)

SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
	id INTEGER PRIMARY KEY,
	login TEXT,
	name TEXT,
	raw_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS taxa (
	id INTEGER PRIMARY KEY,
	name TEXT,
	rank TEXT,
	iconic_taxon_name TEXT,
	ancestry TEXT,
	raw_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS observations (
	id INTEGER PRIMARY KEY,
	observed_on TEXT,
	created_at TEXT,
	updated_at TEXT,
	quality_grade TEXT,
	latitude REAL,
	longitude REAL,
	positional_accuracy REAL,
	geoprivacy TEXT,
	place_guess TEXT,
	species_guess TEXT,
	license TEXT,
	taxon_id INTEGER,
	user_id INTEGER,
	raw_json TEXT NOT NULL,
	FOREIGN KEY (taxon_id) REFERENCES taxa(id) ON DELETE SET NULL,
	FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_obs_coords ON observations(latitude, longitude);
CREATE INDEX IF NOT EXISTS idx_obs_taxon ON observations(taxon_id);
CREATE INDEX IF NOT EXISTS idx_obs_user ON observations(user_id);
CREATE INDEX IF NOT EXISTS idx_obs_quality ON observations(quality_grade);

CREATE TABLE IF NOT EXISTS photos (
	id INTEGER PRIMARY KEY,
	url TEXT,
	license_code TEXT,
	raw_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS observation_photos (
	observation_id INTEGER NOT NULL,
	photo_id INTEGER NOT NULL,
	position INTEGER,
	PRIMARY KEY (observation_id, photo_id),
	FOREIGN KEY (observation_id) REFERENCES observations(id) ON DELETE CASCADE,
	FOREIGN KEY (photo_id) REFERENCES photos(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_obs_photos_obs ON observation_photos(observation_id);

CREATE TABLE IF NOT EXISTS sounds (
	id INTEGER PRIMARY KEY,
	file_url TEXT,
	license_code TEXT,
	raw_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS observation_sounds (
	observation_id INTEGER NOT NULL,
	sound_id INTEGER NOT NULL,
	PRIMARY KEY (observation_id, sound_id),
	FOREIGN KEY (observation_id) REFERENCES observations(id) ON DELETE CASCADE,
	FOREIGN KEY (sound_id) REFERENCES sounds(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_obs_sounds_obs ON observation_sounds(observation_id);

CREATE TABLE IF NOT EXISTS identifications (
	id INTEGER PRIMARY KEY,
	observation_id INTEGER NOT NULL,
	user_id INTEGER,
	taxon_id INTEGER,
	is_current INTEGER,
	created_at TEXT,
	raw_json TEXT NOT NULL,
	FOREIGN KEY (observation_id) REFERENCES observations(id) ON DELETE CASCADE,
	FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL,
	FOREIGN KEY (taxon_id) REFERENCES taxa(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_idents_obs ON identifications(observation_id);
CREATE INDEX IF NOT EXISTS idx_idents_taxon ON identifications(taxon_id);
"""


@contextmanager
def get_db_connection(db_path: str | Path) -> Iterator[sqlite3.Connection]:
	conn = sqlite3.connect(str(db_path))
	conn.row_factory = sqlite3.Row
	try:
		yield conn
	except Exception as exc:
		conn.rollback()
		LOGGER.error("SQLite error: %s", exc)
		raise
	finally:
		conn.close()


def init_db(db_path: str | Path) -> None:
	with get_db_connection(db_path) as conn:
		conn.executescript(SCHEMA)
		conn.commit()
	LOGGER.info("Initialized database at %s", db_path)


def _extract_geojson_coords(obs: Dict[str, Any]) -> tuple[float | None, float | None]:
	geo = obs.get("geojson") or {}
	coords = geo.get("coordinates") or []
	if len(coords) == 2:
		return float(coords[1]), float(coords[0])
	return None, None


def _upsert_user(cursor: sqlite3.Cursor, user: Dict[str, Any] | None) -> int | None:
	if not user or user.get("id") is None:
		return None
	cursor.execute(
		"""
		INSERT OR REPLACE INTO users (id, login, name, raw_json)
		VALUES (?, ?, ?, ?)
		""",
		(
			user.get("id"),
			user.get("login"),
			user.get("name"),
			json.dumps(user, ensure_ascii=False),
		),
	)
	return int(user.get("id"))


def _upsert_taxon(cursor: sqlite3.Cursor, taxon: Dict[str, Any] | None) -> int | None:
	if not taxon or taxon.get("id") is None:
		return None
	cursor.execute(
		"""
		INSERT OR REPLACE INTO taxa (id, name, rank, iconic_taxon_name, ancestry, raw_json)
		VALUES (?, ?, ?, ?, ?, ?)
		""",
		(
			taxon.get("id"),
			taxon.get("name"),
			taxon.get("rank"),
			taxon.get("iconic_taxon_name"),
			taxon.get("ancestry"),
			json.dumps(taxon, ensure_ascii=False),
		),
	)
	return int(taxon.get("id"))


def _upsert_photo(cursor: sqlite3.Cursor, photo: Dict[str, Any]) -> int | None:
	photo_id = photo.get("id")
	if photo_id is None:
		return None
	cursor.execute(
		"""
		INSERT OR REPLACE INTO photos (id, url, license_code, raw_json)
		VALUES (?, ?, ?, ?)
		""",
		(
			photo_id,
			str(photo.get("url", "")),
			photo.get("license_code"),
			json.dumps(photo, ensure_ascii=False),
		),
	)
	return int(photo_id)


def _upsert_sound(cursor: sqlite3.Cursor, sound: Dict[str, Any]) -> int | None:
	sound_id = sound.get("id")
	if sound_id is None:
		return None
	cursor.execute(
		"""
		INSERT OR REPLACE INTO sounds (id, file_url, license_code, raw_json)
		VALUES (?, ?, ?, ?)
		""",
		(
			sound_id,
			sound.get("file_url"),
			sound.get("license_code"),
			json.dumps(sound, ensure_ascii=False),
		),
	)
	return int(sound_id)


def _upsert_observation(cursor: sqlite3.Cursor, obs: Dict[str, Any]) -> None:
	obs_id = obs.get("id")
	if obs_id is None:
		raise ValueError("Observation missing id")

	lat, lon = _extract_geojson_coords(obs)
	taxon_id = _upsert_taxon(cursor, obs.get("taxon"))
	user_id = _upsert_user(cursor, obs.get("user"))

	cursor.execute(
		"""
		INSERT OR REPLACE INTO observations (
			id, observed_on, created_at, updated_at, quality_grade,
			latitude, longitude, positional_accuracy,
			geoprivacy, place_guess, species_guess, license,
			taxon_id, user_id, raw_json
		) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
		""",
		(
			obs_id,
			obs.get("observed_on"),
			obs.get("created_at"),
			obs.get("updated_at"),
			obs.get("quality_grade"),
			lat,
			lon,
			obs.get("positional_accuracy"),
			obs.get("geoprivacy"),
			obs.get("place_guess"),
			obs.get("species_guess"),
			obs.get("license"),
			taxon_id or obs.get("taxon_id"),
			user_id or obs.get("user_id"),
			json.dumps(obs, ensure_ascii=False),
		),
	)

	for index, photo in enumerate(obs.get("photos", [])):
		photo_id = _upsert_photo(cursor, photo)
		if photo_id is None:
			continue
		cursor.execute(
			"""
			INSERT OR REPLACE INTO observation_photos (observation_id, photo_id, position)
			VALUES (?, ?, ?)
			""",
			(obs_id, photo_id, index),
		)

	for sound in obs.get("sounds", []):
		sound_id = _upsert_sound(cursor, sound)
		if sound_id is None:
			continue
		cursor.execute(
			"""
			INSERT OR REPLACE INTO observation_sounds (observation_id, sound_id)
			VALUES (?, ?)
			""",
			(obs_id, sound_id),
		)

	for ident in obs.get("identifications", []):
		ident_id = ident.get("id")
		if ident_id is None:
			continue
		ident_user_id = _upsert_user(cursor, ident.get("user"))
		ident_taxon_id = _upsert_taxon(cursor, ident.get("taxon"))
		cursor.execute(
			"""
			INSERT OR REPLACE INTO identifications (
				id, observation_id, user_id, taxon_id, is_current, created_at, raw_json
			) VALUES (?, ?, ?, ?, ?, ?, ?)
			""",
			(
				ident_id,
				obs_id,
				ident_user_id,
				ident_taxon_id,
				1 if ident.get("current") else 0,
				ident.get("created_at"),
				json.dumps(ident, ensure_ascii=False),
			),
		)


def save_observations(db_path: str | Path, observations: Iterable[Dict[str, Any]]) -> int:
	init_db(db_path)
	count = 0
	with get_db_connection(db_path) as conn:
		cursor = conn.cursor()
		for obs in observations:
			_upsert_observation(cursor, obs)
			count += 1
		conn.commit()
	return count


def save_inat_response(db_path: str | Path, response_json: Dict[str, Any]) -> int:
	results = response_json.get("results")
	if not isinstance(results, list):
		raise ValueError("Invalid iNaturalist response: missing 'results' list")
	return save_observations(db_path, results)


__all__ = [
	"init_db",
	"save_observations",
	"save_inat_response",
	"get_db_connection",
]
