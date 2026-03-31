from __future__ import annotations

import csv
from pathlib import Path
from typing import TypedDict

from app.config import Config

ISO_3166_CSV = Path(__file__).resolve().parent.parent / Config.DATA_DIR / "iso3166_country_codes_continents_modified.csv"

# AI-assisted structure that keeps the dictionary loaded from the CSV consistent.
class _GeoLookup(TypedDict):
    continent_by_iso: dict[str, str]
    continent_name_by_code: dict[str, str]
    continent_code_by_name: dict[str, str]
    country_name_by_code: dict[str, str]
    country_code_a2_by_code: dict[str, str]
    country_code_by_name: dict[str, str]

# Global variable storing the geographic lookup to avoid reloading the CSV on every request.
_geo_lookup: _GeoLookup | None = None


def _clean_str(value: str) -> str:
    """
    Utility function that normalizes lookup keys.
    """
    return value.strip().lower()


def _load_geo_lookup() -> _GeoLookup:
    """
    Load the geographic lookup from the ISO-3166 CSV.

    Built with AI assistance.
    """
    path: Path = ISO_3166_CSV
    if not path.exists():
        raise FileNotFoundError(f"ISO-3166 CSV not found: {path}")

    continent_by_iso_code: dict[str, str] = {}
    continent_name_by_code: dict[str, str] = {}
    continent_code_by_name: dict[str, str] = {}
    country_name_by_code: dict[str, str] = {}
    country_code_a2_by_code: dict[str, str] = {}
    country_code_by_name: dict[str, str] = {}

    with path.open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            code_a2 = row.get("Two_Letter_Country_Code", "").strip().upper()
            code_a3 = row.get("Three_Letter_Country_Code", "").strip().upper()
            continent = row.get("Continent_Name", "").strip()
            continent_code = row.get("Continent_Code", "").strip().upper()
            country_name = row.get("Country_Name", "").strip()
            if not (continent and continent_code and code_a2 and country_name):
                continue

            # Store the values in the lookup dictionaries.
            continent_by_iso_code[code_a2] = continent
            country_name_by_code[code_a2] = country_name
            country_code_a2_by_code[code_a2] = code_a2
            if code_a3:
                continent_by_iso_code[code_a3] = continent
                country_name_by_code[code_a3] = country_name
                country_code_a2_by_code[code_a3] = code_a2

            continent_name_by_code[continent_code] = continent
            continent_code_by_name[_clean_str(continent)] = continent_code

            normalized_country_name = _clean_str(country_name)
            country_code_by_name[normalized_country_name] = code_a2

            # AI-implemented helper.
            #   Add practical aliases for UI/map names (e.g. "France" from
            #   "France, French Republic", and names without parenthetical notes).
            comma_alias = _clean_str(country_name.split(",")[0])
            if comma_alias:
                country_code_by_name.setdefault(comma_alias, code_a2)
            paren_alias = _clean_str(country_name.split("(")[0])
            if paren_alias:
                country_code_by_name.setdefault(paren_alias, code_a2)

    return {
        "continent_by_iso": continent_by_iso_code,
        "continent_name_by_code": continent_name_by_code,
        "continent_code_by_name": continent_code_by_name,
        "country_name_by_code": country_name_by_code,
        "country_code_a2_by_code": country_code_a2_by_code,
        "country_code_by_name": country_code_by_name,
    }


def _get_geo_lookup() -> _GeoLookup:
    """
    Utility function that returns the geographic lookup.
    """
    global _geo_lookup
    if _geo_lookup is None:
        _geo_lookup = _load_geo_lookup()
    return _geo_lookup


def get_continent_names_by_iso() -> dict[str, str]:
    """Utility function that returns a dictionary of continent names indexed by country ISO code."""
    return dict(_get_geo_lookup()["continent_by_iso"])


def get_country_name_by_code(code: str) -> str | None:
    """Utility function that returns the country name from a country code (A2 or A3)."""
    if not code:
        return None
    return _get_geo_lookup()["country_name_by_code"].get(code.strip().upper())


def get_country_code_by_name(name: str) -> str | None:
    """Utility function that returns the country code from the country name."""
    if not name:
        return None
    return _get_geo_lookup()["country_code_by_name"].get(_clean_str(name))


def get_continent_name_by_code(code: str) -> str | None:
    """Utility function that returns the continent name from the continent code."""
    if not code:
        return None
    return _get_geo_lookup()["continent_name_by_code"].get(code.strip().upper())


def get_continent_code_by_name(name: str) -> str | None:
    """Utility function that returns the continent code from the continent name."""
    if not name:
        return None
    return _get_geo_lookup()["continent_code_by_name"].get(_clean_str(name))


def get_country_code_a2_by_code() -> dict[str, str]:
    """Utility function that returns a country's A2 code from either its A2 or A3 code."""
    return dict(_get_geo_lookup()["country_code_a2_by_code"])
