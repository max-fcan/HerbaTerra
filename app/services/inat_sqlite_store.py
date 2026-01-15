"""
iNaturalist SQLite Data Store

This module provides functionality to store iNaturalist observation data
in a SQLite database with proper relational structure.
"""

from __future__ import annotations

import json
import sqlite3
import logging
from contextlib import contextmanager
from typing import Any, Dict, Iterator
from pathlib import Path

from app.logging_config import configure_logging

LOGGER = configure_logging(
    level = logging.DEBUG,
    logger_name = __name__,
    log_filename = "inaturalist_store.log"
)

USABLE_LICENSES = "CC0,CC-BY,CC-BY-SA,CC-BY-ND"  # List formatted for iNaturalist API requests

# =========================
# SCHEMA DEFINITION
# =========================

SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS observations (
    id INTEGER PRIMARY KEY,
    observed_on TEXT,
    created_at TEXT,
    updated_at TEXT,
    latitude REAL,
    longitude REAL,
    positional_accuracy REAL,
    quality_grade TEXT,
    iconic_taxon_name TEXT,
    taxon_id INTEGER,
    taxon_name TEXT,
    user_id INTEGER,
    user_login TEXT,
    raw_json TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_obs_coords ON observations(latitude, longitude);
CREATE INDEX IF NOT EXISTS idx_obs_taxon ON observations(taxon_id);
CREATE INDEX IF NOT EXISTS idx_obs_user ON observations(user_id);
CREATE INDEX IF NOT EXISTS idx_obs_quality ON observations(quality_grade);

CREATE TABLE IF NOT EXISTS photos (
    id INTEGER PRIMARY KEY,
    observation_id INTEGER NOT NULL,
    url TEXT,
    license_code TEXT,
    raw_json TEXT NOT NULL,
    FOREIGN KEY (observation_id) REFERENCES observations(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_photos_obs ON photos(observation_id);

CREATE TABLE IF NOT EXISTS sounds (
    id INTEGER PRIMARY KEY,
    observation_id INTEGER NOT NULL,
    url TEXT,
    license_code TEXT,
    raw_json TEXT NOT NULL,
    FOREIGN KEY (observation_id) REFERENCES observations(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_sounds_obs ON sounds(observation_id);

CREATE TABLE IF NOT EXISTS identifications (
    id INTEGER PRIMARY KEY,
    observation_id INTEGER NOT NULL,
    user_id INTEGER,
    taxon_id INTEGER,
    raw_json TEXT NOT NULL,
    FOREIGN KEY (observation_id) REFERENCES observations(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_idents_obs ON identifications(observation_id);
CREATE INDEX IF NOT EXISTS idx_idents_taxon ON identifications(taxon_id);
"""


# =========================
# DATABASE CONNECTION
# =========================

@contextmanager
def get_db_connection(db_path: str | Path) -> Iterator[sqlite3.Connection]:
    """
    Context manager for database connections with proper resource cleanup.
    
    Args:
        db_path: Path to the SQLite database file
        
    Yields:
        sqlite3.Connection: Active database connection
    """
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    except Exception as e:
        conn.rollback()
        LOGGER.error(f"Database error: {e}")
        raise
    finally:
        conn.close()


def init_db(db_path: str | Path) -> None:
    """
    Initialize the database schema.
    
    Args:
        db_path: Path to the SQLite database file
    """
    with get_db_connection(db_path) as conn:
        conn.executescript(SCHEMA)
        conn.commit()
    LOGGER.info(f"Database initialized at {db_path}")


# =========================
# DATA EXTRACTION
# =========================

def extract_coordinates(obs: Dict[str, Any]) -> tuple[float | None, float | None]:
    """Extract longitude and latitude from observation geojson."""
    geo = obs.get("geojson") or {}
    coords = geo.get("coordinates") or []
    
    if len(coords) == 2:
        return coords[0], coords[1]  # longitude, latitude
    return None, None


def extract_nested_id(data: Dict[str, Any] | None, key: str = "id") -> Any:
    """Safely extract ID from nested dictionary."""
    return data.get(key) if data else None


# =========================
# INSERT OPERATIONS
# =========================

def insert_observation(cursor: sqlite3.Cursor, obs: Dict[str, Any]) -> None:
    """
    Insert a single observation and its related data into the database.
    
    Args:
        cursor: Database cursor within an active transaction
        obs: Observation data from iNaturalist API
    """
    obs_id = obs["id"]
    longitude, latitude = extract_coordinates(obs)
    taxon = obs.get("taxon") or {}
    user = obs.get("user") or {}

    cursor.execute(
        """
        INSERT OR REPLACE INTO observations (
            id, observed_on, created_at, updated_at,
            latitude, longitude, positional_accuracy,
            quality_grade, iconic_taxon_name,
            taxon_id, taxon_name,
            user_id, user_login,
            raw_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            obs_id,
            obs.get("observed_on"),
            obs.get("created_at"),
            obs.get("updated_at"),
            latitude,
            longitude,
            obs.get("positional_accuracy"),
            obs.get("quality_grade"),
            obs.get("iconic_taxon_name"),
            extract_nested_id(taxon),
            taxon.get("name"),
            extract_nested_id(user),
            user.get("login"),
            json.dumps(obs, ensure_ascii=False),
        ),
    )

    # Insert photos
    for photo in obs.get("photos", []):
        cursor.execute(
            """
            INSERT OR REPLACE INTO photos (id, observation_id, url, license_code, raw_json)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                photo.get("id"),
                obs_id,
                str(photo.get("url", "")).replace("square", "original"),
                photo.get("license_code"),
                json.dumps(photo, ensure_ascii=False),
            ),
        )
    # Insert sounds
    for sound in obs.get("sounds", []):
        cursor.execute(
            """
            INSERT OR REPLACE INTO sounds (id, observation_id, url, license_code, raw_json)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                sound.get("id"),
                obs_id,
                sound.get("file_url"),
                sound.get("license_code"),
                json.dumps(sound, ensure_ascii=False),
            ),
        )

    # Insert identifications
    for ident in obs.get("identifications", []):
        cursor.execute(
            """
            INSERT OR REPLACE INTO identifications (id, observation_id, user_id, taxon_id, raw_json)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                ident.get("id"),
                obs_id,
                extract_nested_id(ident.get("user")),
                extract_nested_id(ident.get("taxon")),
                json.dumps(ident, ensure_ascii=False),
            ),
        )


def save_inat_response(db_path: str | Path, response_json: Dict[str, Any]) -> int:
    """
    Save iNaturalist API response to the database.
    
    Args:
        db_path: Path to the SQLite database file
        response_json: JSON response from iNaturalist API
        
    Returns:
        Number of observations saved
        
    Raises:
        ValueError: If response format is invalid
    """
    results = response_json.get("results")
    if not isinstance(results, list):
        raise ValueError("Invalid iNaturalist response: missing or invalid 'results' field")
    
    if not results:
        LOGGER.warning("No observations to save")
        return 0

    init_db(db_path)
    
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        
        for obs in results:
            try:
                insert_observation(cursor, obs)
            except Exception as e:
                LOGGER.error(f"Failed to insert observation {obs.get('id')}: {e}")
                raise
        
        conn.commit()
    
    LOGGER.info(f"Successfully saved {len(results)} observations to {db_path}")
    return len(results)


# =========================
# QUERY HELPERS
# =========================

def get_observation_count(db_path: str | Path) -> int:
    """Get the total number of observations in the database."""
    with get_db_connection(db_path) as conn:
        cursor = conn.execute("SELECT COUNT(*) FROM observations")
        return cursor.fetchone()[0]


def get_observations_by_taxon(db_path: str | Path, taxon_id: int) -> list[Dict[str, Any]]:
    """Retrieve all observations for a specific taxon."""
    with get_db_connection(db_path) as conn:
        cursor = conn.execute(
            "SELECT * FROM observations WHERE taxon_id = ?",
            (taxon_id,)
        )
        return [dict(row) for row in cursor.fetchall()]


# =========================
# MAIN EXECUTION
# =========================

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    from .inaturalist_api import get_observations
    
    db_path = "inat_test.db"
    
    print(f"Fetching observations from iNaturalist API...")
    response = get_observations(
        per_page=100,
        page=1,
        license=USABLE_LICENSES.split(","),
        photos=True,
        geo=True,
        iconic_taxa=["Plantae"],
        order_by="id",
        order="asc",
    )
    
    count = save_inat_response(db_path, response)
    print(f"✓ Saved {count} observations to {db_path}")
    print(f"✓ Total observations in database: {get_observation_count(db_path)}")