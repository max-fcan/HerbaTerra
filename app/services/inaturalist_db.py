"""
SQLite storage layer for iNaturalist observations.

Normalizes iNaturalist JSON into relational tables and preserves raw JSON.
"""

from __future__ import annotations

import json
import logging
import sqlite3
import zlib
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator

from app.logging_config import configure_logging

LOGGER = configure_logging(
	level=logging.INFO,
	logger_name=__name__,
	log_filename="inaturalist_db.log",
)


def _compress_json(obj: Any) -> bytes:
	"""Compress a JSON-serializable object to gzipped bytes."""
	return zlib.compress(json.dumps(obj, ensure_ascii=False).encode("utf-8"), level=6)


def _decompress_json(data: bytes) -> Any:
	"""Decompress gzipped bytes back to a Python object."""
	return json.loads(zlib.decompress(data).decode("utf-8"))


SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
	id INTEGER PRIMARY KEY,
	login TEXT,
	name TEXT,
	raw_json BLOB NOT NULL
);

CREATE TABLE IF NOT EXISTS taxa (
	id INTEGER PRIMARY KEY,
	name TEXT,
	rank TEXT,
	iconic_taxon_name TEXT,
	ancestry TEXT,
	raw_json BLOB NOT NULL
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
	raw_json BLOB NOT NULL,
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
	raw_json BLOB NOT NULL
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
	raw_json BLOB NOT NULL
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
	raw_json BLOB NOT NULL,
	FOREIGN KEY (observation_id) REFERENCES observations(id) ON DELETE CASCADE,
	FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL,
	FOREIGN KEY (taxon_id) REFERENCES taxa(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_idents_obs ON identifications(observation_id);
CREATE INDEX IF NOT EXISTS idx_idents_taxon ON identifications(taxon_id);

CREATE TABLE IF NOT EXISTS location_tags (
	observation_id INTEGER PRIMARY KEY,
	city TEXT,
	admin1 TEXT,
	admin2 TEXT,
	country TEXT,
	continent TEXT,
	error TEXT,
	FOREIGN KEY (observation_id) REFERENCES observations(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_location_country ON location_tags(country);
CREATE INDEX IF NOT EXISTS idx_location_continent ON location_tags(continent);
"""


@contextmanager
def get_db_connection(db_path: str | Path) -> Iterator[sqlite3.Connection]:
	conn = sqlite3.connect(str(db_path))
	conn.row_factory = sqlite3.Row
	_configure_connection(conn)
	try:
		yield conn
	except Exception as exc:
		conn.rollback()
		LOGGER.error("SQLite error: %s", exc)
		raise
	finally:
		conn.close()


def _configure_connection(conn: sqlite3.Connection) -> None:
	conn.execute("PRAGMA foreign_keys = ON;")
	conn.execute("PRAGMA journal_mode = WAL;")
	conn.execute("PRAGMA synchronous = NORMAL;")


def init_db(db_path: str | Path) -> None:
	with get_db_connection(db_path) as conn:
		conn.executescript(SCHEMA)
		conn.commit()
	LOGGER.info("Initialized database at %s", db_path)


def _extract_coords(obs: Dict[str, Any]) -> tuple[float | None, float | None]:
	"""Extract latitude and longitude from observation.
	
	Tries direct latitude/longitude fields first (may be strings),
	then falls back to geojson.coordinates if available.
	"""
	# Try direct lat/lon fields first (API returns these as strings)
	lat = obs.get("latitude")
	lon = obs.get("longitude")
	if lat is not None and lon is not None:
		try:
			return float(lat), float(lon)
		except (ValueError, TypeError):
			pass
	
	# Fallback to geojson if available
	geo = obs.get("geojson") or {}
	coords = geo.get("coordinates") or []
	if len(coords) == 2:
		try:
			return float(coords[1]), float(coords[0])
		except (ValueError, TypeError):
			pass
	
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
			_compress_json(user),
		),
	)
	return int(user.get("id")) # pyright: ignore[reportArgumentType]


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
			_compress_json(taxon),
		),
	)
	return int(taxon.get("id")) # pyright: ignore[reportArgumentType]


def _extract_photo_url(photo: Dict[str, Any]) -> str:
	"""Extract the best available photo URL, preferring original quality.
	
	The API provides square_url, thumb_url, small_url, medium_url, large_url.
	We convert square_url to original by replacing '/square.' with '/original.'.
	"""
	square_url = photo.get("square_url")
	if square_url:
		# Convert square URL to original: .../square.jpg -> .../original.jpg
		return square_url.replace("/square.", "/original.")
	
	# Fallback to best available size
	for size in ["large_url", "medium_url", "small_url", "thumb_url"]:
		url = photo.get(size)
		if url:
			return url
	
	return ""


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
			_extract_photo_url(photo),
			photo.get("license_code"),
			_compress_json(photo),
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
			_compress_json(sound),
		),
	)
	return int(sound_id)


def _upsert_observation(cursor: sqlite3.Cursor, obs: Dict[str, Any]) -> None:
	obs_id = obs.get("id")
	if obs_id is None:
		raise ValueError("Observation missing id")

	lat, lon = _extract_coords(obs)
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
			taxon_id,
			user_id,
		_compress_json(obs),
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
				_compress_json(ident),
			),
		)


def _save_observations(cursor: sqlite3.Cursor, observations: Iterable[Dict[str, Any]]) -> int:
	count = 0
	for obs in observations:
		_upsert_observation(cursor, obs)
		count += 1
	return count


def save_observations(
	db_path: str | Path,
	observations: Iterable[Dict[str, Any]],
	*,
	connection: sqlite3.Connection | None = None,
	commit: bool = True,
	initialize: bool = True,
) -> int:
	if connection is None:
		if initialize:
			init_db(db_path)
		with get_db_connection(db_path) as conn:
			cursor = conn.cursor()
			count = _save_observations(cursor, observations)
			if commit:
				conn.commit()
			return count

	if initialize:
		connection.executescript(SCHEMA)
	cursor = connection.cursor()
	count = _save_observations(cursor, observations)
	if commit:
		connection.commit()
	return count


def save_inat_response(
	db_path: str | Path,
	response_json: Dict[str, Any],
	*,
	connection: sqlite3.Connection | None = None,
	commit: bool = True,
	initialize: bool = True,
) -> int:
	results = response_json.get("results")
	if not isinstance(results, list):
		raise ValueError("Invalid iNaturalist response: missing 'results' list")
	return save_observations(
		db_path,
		results,
		connection=connection,
		commit=commit,
		initialize=initialize,
	)


def enrich_observations_with_location_tags(
	db_path: str | Path,
	*,
	connection: sqlite3.Connection | None = None,
	batch_size: int = 1000,
	skip_existing: bool = True,
) -> int:
	"""
	Reverse geocode observations that have coordinates but no location tags.
	
	Args:
		db_path: Path to the SQLite database
		connection: Optional existing connection to reuse
		batch_size: Number of observations to process at once
		skip_existing: Skip observations that already have location tags
	
	Returns:
		Number of observations tagged
	"""
	from app.workers.location_tags import LocationTagger
	
	def _process_batch(conn: sqlite3.Connection) -> int:
		cursor = conn.cursor()
		
		# Find observations with coordinates but no location tags
		if skip_existing:
			query = """
				SELECT o.id, o.latitude, o.longitude
				FROM observations o
				LEFT JOIN location_tags lt ON o.id = lt.observation_id
				WHERE o.latitude IS NOT NULL 
				  AND o.longitude IS NOT NULL
				  AND lt.observation_id IS NULL
				LIMIT ?
			"""
		else:
			query = """
				SELECT id, latitude, longitude
				FROM observations
				WHERE latitude IS NOT NULL AND longitude IS NOT NULL
				LIMIT ?
			"""
		
		cursor.execute(query, (batch_size,))
		rows = cursor.fetchall()
		
		if not rows:
			return 0
		
		# Prepare coordinates for batch reverse geocoding
		# Group observations by coordinates to handle duplicates
		tagger = LocationTagger()
		coords_to_obs_ids = {}
		for obs_id, lat, lon in rows:
			coord = (lat, lon)
			if coord not in coords_to_obs_ids:
				coords_to_obs_ids[coord] = []
			coords_to_obs_ids[coord].append(obs_id)
		
		coords_list = list(coords_to_obs_ids.keys())
		
		# Batch reverse geocode
		tags_map = tagger.reverse_geocode_many(coords_list)
		
		# Insert location tags for all observations at each coordinate
		for coord, tags in tags_map.items():
			for obs_id in coords_to_obs_ids[coord]:
				cursor.execute(
					"""
					INSERT OR REPLACE INTO location_tags (
						observation_id, city, admin1, admin2, country, continent, error
					) VALUES (?, ?, ?, ?, ?, ?, ?)
					""",
					(
						obs_id,
						tags.city,
						tags.admin1,
						tags.admin2,
						tags.country,
						tags.continent,
						tags.error,
					),
				)
		
		conn.commit()
		return len(rows)
	
	if connection:
		return _process_batch(connection)
	
	total_tagged = 0
	with get_db_connection(db_path) as conn:
		while True:
			tagged = _process_batch(conn)
			total_tagged += tagged
			if tagged < batch_size:
				break
			LOGGER.info("Tagged %d observations so far...", total_tagged)
	
	LOGGER.info("Completed location tagging: %d observations", total_tagged)
	return total_tagged


__all__ = [
	"init_db",
	"save_observations",
	"save_inat_response",
	"get_db_connection",
	"enrich_observations_with_location_tags",
]
