"""
Reverse geocoding helpers with continent tagging.

Usage::

    from app.services.geocoding import (
        reverse_geocode,
        reverse_geocode_many,
        country_code_to_continent,
        country_code_to_country_name,
        LocationTagger,
    )
"""

from __future__ import annotations

import csv
import logging
from functools import cache
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, Mapping, Optional, Sequence, Tuple

import reverse_geocoder as rg

log = logging.getLogger(__name__)

# From https://gist.github.com/stevewithington/20a69c0b6d2ff846ea5d35e5fc47f26c
_COUNTRY_CONTINENT_CSV = Path("app/static/data/iso3166_country_codes_continents.csv")
_COUNTRY_CONTINENT_MODIFIED_CSV = Path("app/static/data/iso3166_country_codes_continents_modified.csv")


@dataclass(frozen=True, slots=True)
class LocationTags:
    """Container for normalized reverse geocode output."""

    city: Optional[str] = None
    admin1: Optional[str] = None
    admin2: Optional[str] = None
    country: Optional[str] = None
    continent: Optional[str] = None
    error: Optional[str] = None

    def location_as_str(self) -> str:
        """Return a human-readable location string."""
        return ", ".join(
            p for p in [self.continent, self.country, self.admin1, self.admin2, self.city] if p
        )

    def as_dict(self) -> Dict[str, Optional[str]]:
        return {
            "continent": self.continent,
            "country": self.country,
            "city": self.city,
            "admin1": self.admin1,
            "admin2": self.admin2,
            "error": self.error,
        }


def _normalize_coordinate(coord: Tuple[float, float]) -> Optional[Tuple[float, float]]:
    """Validate and normalize a (lat, lon) tuple to floats within valid ranges."""
    try:
        lat = float(coord[0])
        lon = float(coord[1])
    except (TypeError, ValueError, IndexError):
        log.warning("Invalid coordinate %s; expected a 2-tuple of numbers", coord)
        return None

    if not (-90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0):
        log.warning("Coordinate out of bounds: %s", coord)
        return None

    return (lat, lon)


@cache
def _load_country_code_mapping(csv_path: Path | str = _COUNTRY_CONTINENT_CSV) -> Dict[str, Dict[str, str]]:
    """Load country → continent mappings from CSV."""
    csv_path = Path(csv_path)

    if not csv_path.exists():
        log.error("Expected country mapping file at %s but it is missing", csv_path)
        raise FileNotFoundError(f"Country mapping file missing: {csv_path}")

    mapping: Dict[str, Dict[str, str]] = {}
    with csv_path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for idx, row in enumerate(reader, start=2):
            code = (row.get("Two_Letter_Country_Code") or "").strip().upper()
            country = (row.get("Country_Name") or "").split(",")[0].strip()
            continent = (row.get("Continent_Name") or "").strip()
            if not code or not continent or not country:
                log.debug("Skipping row %s with incomplete data: %s", idx, row)
                continue

            existing = mapping.get(code)
            if existing and existing != continent:
                log.warning(
                    "Country code %s maps to multiple continents (%s, %s)",
                    code, existing, continent,
                )
            mapping[code] = {"country": country, "continent": continent}

    if not mapping:
        log.error("No country/continent mappings loaded from %s", csv_path)
        raise ValueError(f"No country/continent mappings found in {csv_path}")

    log.info("Loaded %s country/continent mappings from %s", len(mapping), csv_path)
    return mapping


class LocationTagger:
    """Reverse geocode coordinates and enrich with continent information."""

    def __init__(self, country_continent_csv: Path | str = _COUNTRY_CONTINENT_CSV):
        self.country_continent_csv = Path(country_continent_csv)
        self._country_to_continent: Dict[str, Dict[str, str]] = _load_country_code_mapping(
            self.country_continent_csv
        )

    def country_code_to_continent(self, country_code: str) -> Optional[str]:
        code = (country_code or "").strip().upper()
        if code:
            return self._country_to_continent.get(code, {}).get("continent")
        return None

    def country_code_to_country_name(self, country_code: str) -> Optional[str]:
        code = (country_code or "").strip().upper()
        if code:
            return self._country_to_continent.get(code, {}).get("country")
        return None

    def _build_tags(self, match: Mapping[str, str] | None) -> LocationTags:
        if not match:
            return LocationTags()
        country_code = (match.get("cc") or "").strip().upper()
        country_data = self._country_to_continent.get(country_code, {})
        return LocationTags(
            city=match.get("name", ""),
            admin1=match.get("admin1", ""),
            admin2=match.get("admin2", ""),
            continent=country_data.get("continent"),
            country=country_data.get("country"),
        )

    def _search(self, coordinates: Sequence[Tuple[float, float]]) -> list[Mapping[str, str]]:
        if not coordinates:
            return []
        try:
            return rg.search(coordinates)
        except Exception:
            log.exception("reverse_geocoder.search failed for %s coordinate(s)", len(coordinates))
            return []

    def reverse_geocode(self, latitude: float, longitude: float) -> LocationTags:
        """Reverse geocode a single coordinate pair (lat, lon)."""
        normalized = _normalize_coordinate((latitude, longitude))
        if not normalized:
            return LocationTags(error="Invalid")

        matches = self._search([normalized])
        if not matches:
            log.info("No reverse geocode result for %s", normalized)
            return LocationTags(error="NotFound")

        tags = self._build_tags(matches[0])
        log.debug("Reverse geocoded %s -> %s", normalized, tags)
        return tags

    def reverse_geocode_many(
        self, coordinates: Iterable[Tuple[float, float]]
    ) -> Dict[Tuple[float, float], LocationTags]:
        """Reverse geocode multiple coordinate pairs (lat, lon)."""
        normalized_coords: list[Tuple[Tuple[float, float], Tuple[float, float]]] = []
        output: Dict[Tuple[float, float], LocationTags] = {}

        for coord in coordinates:
            normalized = _normalize_coordinate(coord)
            if not normalized:
                output[coord] = LocationTags(error="Invalid")
                continue
            normalized_coords.append((coord, normalized))

        if not normalized_coords:
            return output

        matches = self._search([coord for _, coord in normalized_coords])
        if len(matches) != len(normalized_coords):
            log.warning(
                "reverse_geocoder returned %s result(s) for %s coordinate(s)",
                len(matches), len(normalized_coords),
            )

        for idx, (original, _) in enumerate(normalized_coords):
            match = matches[idx] if idx < len(matches) else None
            output[original] = self._build_tags(match)

        return output


# ── Module-level convenience helpers ────────────────────────────────────────

DEFAULT_TAGGER: LocationTagger | None = None


def _default_tagger() -> LocationTagger:
    global DEFAULT_TAGGER
    if DEFAULT_TAGGER is None:
        DEFAULT_TAGGER = LocationTagger(country_continent_csv=_COUNTRY_CONTINENT_MODIFIED_CSV)
    return DEFAULT_TAGGER


def country_code_to_continent(country_code: str) -> Optional[str]:
    return _default_tagger().country_code_to_continent(country_code)


def country_code_to_country_name(country_code: str) -> Optional[str]:
    return _default_tagger().country_code_to_country_name(country_code)


def reverse_geocode(latitude: float, longitude: float) -> LocationTags:
    return _default_tagger().reverse_geocode(latitude, longitude)


def reverse_geocode_many(
    coordinates: list[Tuple[float, float]],
) -> Dict[Tuple[float, float], LocationTags]:
    tags = _default_tagger().reverse_geocode_many(coordinates)
    return {coord: tag.as_dict() for coord, tag in tags.items()}
