"""Reverse geocoding helpers with continent tagging and structured logging."""

from __future__ import annotations

import csv
import logging
from functools import cache
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, Mapping, Optional, Sequence, Tuple

import reverse_geocoder as rg

from app.logging_config import configure_logging

# From https://gist.github.com/stevewithington/20a69c0b6d2ff846ea5d35e5fc47f26c
_COUNTRY_CONTINENT_CSV = Path("app/static/data/iso3166_country_codes_continents.csv")
_COUNTRY_CONTINENT_MODIFIED_CSV = Path("app/static/data/iso3166_country_codes_continents_modified.csv")

def _get_logger(name: str = __name__) -> logging.Logger:
    """
    Ensure the module logger is wired up.

    If logging has not yet been configured (no root handlers), we configure a rotating
    worker log using the shared configure_logging helper. Otherwise, we attach a
    NullHandler and allow propagation to the already-configured root handlers.
    """
    root_logger = logging.getLogger()
    if not root_logger.handlers:
        try:
            return configure_logging(
                name=name,
                level=logging.INFO,
                log_dir="logs",
                log_filename="workers.log",
                max_bytes=5 * 1024 * 1024,
                backup_count=3,
                in_terminal=True,
            )
        except Exception:
            # Fallback to a quiet logger if configuration fails for any reason.
            fallback = logging.getLogger(name)
            fallback.addHandler(logging.NullHandler())
            fallback.setLevel(logging.NOTSET)
            return fallback

    logger_instance = logging.getLogger(name)
    if not logger_instance.handlers:
        logger_instance.addHandler(logging.NullHandler())
    logger_instance.setLevel(logging.NOTSET)
    return logger_instance


LOGGER = _get_logger()


@dataclass(frozen=True)
class LocationTags:
    """Container for normalized reverse geocode output."""

    city: Optional[str] = None
    admin1: Optional[str] = None
    admin2: Optional[str] = None
    country: Optional[str] = None
    continent: Optional[str] = None
    error: Optional[str] = None

    def as_dict(self) -> Dict[str, Optional[str]]:
        return {
            "continent": self.continent,
            "country": self.country,
            "city": self.city,
            "admin1": self.admin1,
            "admin2": self.admin2,
            "error": self.error,
        }


def _normalize_coordinate(coord: Tuple[float, float]) -> Tuple[float, float] | Optional[int]:
    """Validate and normalize a (lat, lon) tuple to floats within valid ranges."""
    try:
        lat = float(coord[0])
        lon = float(coord[1])
    except (TypeError, ValueError, IndexError):
        LOGGER.warning("Invalid coordinate %s; expected a 2-tuple of numbers", coord)
        return None

    if not (-90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0):
        LOGGER.warning("Coordinate out of bounds (lat, lon): %s", coord)
        return 1

    return (lat, lon)


@cache
def _load_country_code_mapping(csv_path: Path | str = _COUNTRY_CONTINENT_CSV) -> Dict[str, Dict[str, str]]:
    """
    Load country ⇒ continent mappings from the provided CSV file.

    Expects the Github iso3166 "Country and Continent Codes List" CSV with at least:
      - Two_Letter_Country_Code
      - Country_Name
      - Continent_Name
    """
    # Validate CSV path
    try:
        csv_path = Path(csv_path)
    except Exception as e:
        LOGGER.error("Invalid path for country mapping CSV: %s", csv_path)
        raise e
    
    if not csv_path.exists():
        LOGGER.error("Expected country mapping file at %s but it is missing", csv_path)
        raise FileNotFoundError(f"Country mapping file missing: {csv_path}")

    mapping: Dict[str, Dict[str, str]] = {}
    with csv_path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for idx, row in enumerate(reader, start=2):  # start=2 accounts for header row
            code = (row.get("Two_Letter_Country_Code") or "").strip().upper()
            country = (row.get("Country_Name") or "").split(',')[0].strip()
            continent = (row.get("Continent_Name") or "").strip()
            if not code or not continent or not country:
                LOGGER.debug("Skipping row %s with incomplete data: %s", idx, row)
                continue

            existing = mapping.get(code)
            if existing and existing != continent:
                LOGGER.warning(
                    "Country code %s maps to multiple continents (%s, %s)",
                    code,
                    existing,
                    continent,
                )
            mapping[code] = {'country': country, 'continent': continent}

    if not mapping:
        LOGGER.error("No country/continent mappings loaded from %s", csv_path)
        raise ValueError(f"No country/continent mappings found in {csv_path}")

    LOGGER.info("Loaded %s country/continent mappings from %s", len(mapping), csv_path)
    return mapping


class LocationTagger:
    """Reverse geocode coordinates and enrich with continent information."""

    def __init__(self, country_continent_csv: Path | str = _COUNTRY_CONTINENT_CSV):
        self.country_continent_csv = Path(country_continent_csv)
        self._country_to_continent: Dict[str, Dict[str, str]] = _load_country_code_mapping(self.country_continent_csv)
        self._logger = LOGGER

    def country_code_to_continent(self, country_code: str) -> Optional[str]:
        """Return a continent name for a two-letter country code."""
        code = (country_code or "").strip().upper()
        if not code:
            return None
        return self._country_to_continent.get(code, {}).get("continent")

    def country_code_to_country_name(self, country_code: str) -> Optional[str]:
        """Return a country name for a two-letter country code."""
        code = (country_code or "").strip().upper()
        if not code:
            return None
        return self._country_to_continent.get(code, {}).get("country")

    def _build_tags(self, match: Mapping[str, str] | None) -> LocationTags:
        if not match:
            return LocationTags()

        country_code = (match.get("cc") or "").strip().upper()
        return LocationTags(
            city=match.get("name", ""),
            admin1=match.get("admin1", ""),
            admin2=match.get("admin2", ""),
            continent=self.country_code_to_continent(country_code),
            country=self.country_code_to_country_name(country_code),
        )

    def _search(self, coordinates: Sequence[Tuple[float, float]]) -> list[Mapping[str, str]]:
        if not coordinates:
            return []

        try:
            return rg.search(list(coordinates))
        except Exception:
            self._logger.exception(
                "reverse_geocoder.search failed for %s coordinate(s)", len(coordinates)
            )
            return []

    def reverse_geocode(self, latitude: float, longitude: float) -> LocationTags:
        """
        Reverse geocode a single coordinate pair (lat, lon).

        Returns a LocationTags instance with name, admin1, admin2, cc, and continent.
        """
        # Normalize and validate input coordinates
        normalized = _normalize_coordinate((latitude, longitude))
        if normalized == 1:
            return LocationTags(error="OOB")
        elif not normalized or isinstance(normalized, int):
            return LocationTags(error="Invalid")

        # Perform reverse geocoding
        matches = self._search([normalized])
        if not matches:
            self._logger.info("No reverse geocode result for %s", normalized)
            return LocationTags(error="NotFound")

        # Build and return tags from the first (and only) result
        tags = self._build_tags(matches[0])
        self._logger.debug("Reverse geocoded %s -> %s", normalized, tags)
        return tags

    def reverse_geocode_many(
        self, coordinates: Iterable[Tuple[float, float]]
    ) -> Dict[Tuple[float, float], LocationTags]:
        """
        Reverse geocode multiple coordinate pairs (lat, lon).

        Returns a mapping from (lat, lon) to LocationTags.
        """
        normalized_coords: list[Tuple[Tuple[float, float], Tuple[float, float]]] = []
        output: Dict[Tuple[float, float], LocationTags] = {}

        for coord in coordinates:
            normalized = _normalize_coordinate(coord)
            if normalized == 1:
                output[coord] = LocationTags(error="OOB")
                continue
            elif not normalized or isinstance(normalized, int):
                output[coord] = LocationTags(error="Invalid")
                continue
            normalized_coords.append((coord, normalized))
            
        if not normalized_coords:
            return output

        matches = self._search([coord for _, coord in normalized_coords])
        if len(matches) != len(normalized_coords):
            self._logger.warning(
                "reverse_geocoder returned %s result(s) for %s coordinate(s)",
                len(matches),
                len(normalized_coords),
            )

        for idx, (original, _) in enumerate(normalized_coords):
            match = matches[idx] if idx < len(matches) else None
            output[original] = self._build_tags(match)

        return output


# Shared module-level tagger so callers can use simple helper functions, created lazily
DEFAULT_TAGGER: LocationTagger | None = None


def _default_tagger() -> LocationTagger:
    global DEFAULT_TAGGER
    if DEFAULT_TAGGER is None:
        DEFAULT_TAGGER = LocationTagger(country_continent_csv=_COUNTRY_CONTINENT_MODIFIED_CSV) # temp TODO: change from modified to official with country stored as lists
    return DEFAULT_TAGGER


def country_code_to_continent(country_code: str) -> Optional[str]:
    """Return a continent name for a two-letter country code."""
    return _default_tagger().country_code_to_continent(country_code)

def country_code_to_country_name(country_code: str) -> Optional[str]:
    """Return a country name for a two-letter country code."""
    return _default_tagger().country_code_to_country_name(country_code)

def reverse_geocode(latitude: float, longitude: float) -> Dict[str, Optional[str]]:
    """
    Reverse geocode a single coordinate pair (lat, lon).

    Returns a dict with country, city, admin1, admin2, and continent.
    """
    return _default_tagger().reverse_geocode(latitude, longitude).as_dict()


def reverse_geocode_many(
    coordinates: list[Tuple[float, float]],
) -> Dict[Tuple[float, float], Dict[str, Optional[str]]]:
    """
    Reverse geocode multiple coordinate pairs (lat, lon).

    Returns a mapping from (lat, lon) to the location dict.
    """
    tags = _default_tagger().reverse_geocode_many(coordinates)
    return {coord: tag.as_dict() for coord, tag in tags.items()}


if __name__ == "__main__":
    sample_points = [
        (48.8584, 2.2945),  # Paris
        (40.7128, -74.0060),  # New York
        (-33.8688, 151.2093),  # Sydney
        (180, 180),  # Invalid coordinates
    ]

    print("Reverse geocoding sample points...")
    tagger = _default_tagger()
    for coord, info in tagger.reverse_geocode_many(sample_points).items():
        lat, lon = coord
        print(f"{lat:.4f},{lon:.4f} -> {info.as_dict()}")
