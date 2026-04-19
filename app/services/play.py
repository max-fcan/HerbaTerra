from __future__ import annotations

import csv
import random
import re
from functools import lru_cache
from math import asin, cos, pow, radians, sin, sqrt
from pathlib import Path
from typing import Any

from app.db.connections import get_local_db
from app.services.geocoding import (
    get_continent_code_by_name,
    get_continent_name_by_code,
    get_continent_names_by_iso,
    get_country_name_by_code,
)

WORLD_SCOPE = "world"
CONTINENT_SCOPE = "continent"
COUNTRY_SCOPE = "country"
MAX_ROUND_SCORE = 5000
# World-scope anchor: the scale used when the entire Earth is the play area.
# All country scopes produce a strictly smaller scale (harder scoring) via
# sqrt(country_area / EARTH_AREA_KM2).
MIN_REFERENCE_DISTANCE_METERS = 150.0
EARTH_AREA_KM2 = 510_072_000.0
ROUNDING_TARGET_RATIO = (MAX_ROUND_SCORE - 0.5) / MAX_ROUND_SCORE


def _clean_str(value: Any) -> str:
    """
    Utility function that cleans string values.
    """
    return "" if value is None else str(value).strip()


def _format_vernacular_name(raw_name: str, scientific_name: str) -> str:
    """
    Convert the vernacular name to title case and remove the genus name in parentheses when present.
    Built with AI assistance.
    """
    vernacular = _clean_str(raw_name)
    if not vernacular:
        return ""

    genus = _clean_str(scientific_name).split(" ")[0]
    if genus:
        genus_pattern = re.compile(rf"\(\s*{re.escape(genus)}\s*\)", re.IGNORECASE)
        vernacular = genus_pattern.sub("", vernacular)

    vernacular = re.sub(r"\s+", " ", vernacular).strip(" -_,.;:")
    return vernacular.title()


@lru_cache(maxsize=1)
def _load_country_areas_by_code() -> dict[str, float]:
    """
    Load country areas from the CSV keyed by ISO country code.
    """
    country_areas_path = Path(__file__).resolve().parents[2] / "data" / "country_areas.csv"
    country_areas: dict[str, float] = {}

    with country_areas_path.open("r", encoding="utf-8-sig", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        for row in reader:
            country_code = _clean_str(row.get("country_code")).upper()
            area_square_km_raw = row.get("area_square_km")
            try:
                area_square_km = float(area_square_km_raw) if area_square_km_raw else 0.0
            except (TypeError, ValueError):
                area_square_km = 0.0
            if country_code and area_square_km > 0:
                country_areas[country_code] = area_square_km

    return country_areas



@lru_cache(maxsize=1)
def _get_available_world_continent_codes() -> list[str]:
    """
    Return the list of continent codes available in the database.
    """
    continent_names_by_iso = get_continent_names_by_iso()
    
    # Get existing country codes from the species_country_stats table.
    existing_country_codes = get_local_db().execute(
        """
        SELECT DISTINCT country_code
        FROM species_country_stats
        WHERE country_code IS NOT NULL
        """
    ).fetchall()
            
    return list(set(
        continent_code
        for row in existing_country_codes
        if (country_code := _clean_str(row["country_code"]))
        and (continent_code := get_continent_code_by_name(continent_names_by_iso.get(country_code.upper(), "")))
    ))


def parse_play_scope(args: Any) -> dict[str, str]:
    """
    Parse scope parameters to determine the scope type and associated codes.
    """
    country_code = _clean_str(args.get("country_code")).upper()
    continent_code = _clean_str(args.get("continent_code")).upper()

    if country_code:
        normalized_country_name = get_country_name_by_code(country_code)
        if normalized_country_name:
            continent_names_by_iso = get_continent_names_by_iso()
            continent_name = continent_names_by_iso.get(country_code, "")
            continent_code = _clean_str(get_continent_code_by_name(continent_name)).upper()
            return {
                "scope_type": COUNTRY_SCOPE,
                "country_code": country_code,
                "country": normalized_country_name,
                "continent_code": continent_code,
                "continent": continent_name,
            }

    if continent_code:
        normalized_continent_name = get_continent_name_by_code(continent_code)
        if normalized_continent_name:
            return {
                "scope_type": CONTINENT_SCOPE,
                "country_code": "",
                "country": "",
                "continent_code": continent_code,
                "continent": normalized_continent_name,
            }

    return {
        "scope_type": WORLD_SCOPE,
        "country_code": "",
        "country": "",
        "continent_code": "",
        "continent": "",
    }


def _build_world_weights(continent_codes: list[str], antarctica_probability: float = 0.05) -> list[float]:
    """
    Build continent weights, giving Antarctica a specific probability and distributing the remainder evenly across the other continents.
    """
    if not continent_codes:
        return []
    if "AN" not in continent_codes or len(continent_codes) == 1:
        return [1 / len(continent_codes)] * len(continent_codes)
    p_an = max(0.0, min(0.95, antarctica_probability))
    p_other = (1 - p_an) / (len(continent_codes) - 1)
    return [p_an if code == "AN" else p_other for code in continent_codes]


def build_round_plan(
    scope: dict[str, str],
    total_rounds: int,
    world_antarctica_probability: float = 1/20,
) -> list[dict[str, Any]]:
    """
    Build the round plan for the game.
    """
    round_count = max(1, int(total_rounds))  # Ensure there is at least 1 round.
    scope_type = scope.get("scope_type") or WORLD_SCOPE

    if scope_type == WORLD_SCOPE:
        continent_codes = _get_available_world_continent_codes()
        if not continent_codes:
            return []

        weights = _build_world_weights(continent_codes, world_antarctica_probability)
        selected_codes = random.choices(continent_codes, weights=weights, k=round_count)
        return [
            {
                "round_index": index,
                "scope_type": CONTINENT_SCOPE,
                "country_code": "",
                "country": "",
                "continent_code": continent_code,
                "continent": get_continent_name_by_code(continent_code) or continent_code,
            }
            for index, continent_code in enumerate(selected_codes)
        ]

    return [
        {
            "round_index": index,
            "scope_type": scope_type,
            "country_code": scope.get("country_code", ""),
            "country": scope.get("country", ""),
            "continent_code": scope.get("continent_code", ""),
            "continent": scope.get("continent", ""),
        }
        for index in range(round_count)
    ]


def haversine_distance_km(
    latitude_a: float,
    longitude_a: float,
    latitude_b: float,
    longitude_b: float,
) -> float:
    """
    Calculate the haversine distance in kilometers between two points.
    """
    earth_radius_km = 6371.0
    delta_latitude = radians(latitude_b - latitude_a)
    delta_longitude = radians(longitude_b - longitude_a)
    latitude_a_rad = radians(latitude_a)
    latitude_b_rad = radians(latitude_b)

    h = (
        sin(delta_latitude / 2) ** 2
        + cos(latitude_a_rad) * cos(latitude_b_rad) * sin(delta_longitude / 2) ** 2
    )
    return 2 * earth_radius_km * asin(sqrt(h))


@lru_cache(maxsize=256)
def _get_scope_scale_meters_cached(country_code: str, continent_code: str) -> float:
    """
    Return the scoring distance scale in meters for the current scope.

    MIN_REFERENCE_DISTANCE_METERS is the anchor for the full Earth (world scope).
    Country scopes scale down proportionally to sqrt(country_area / EARTH_AREA_KM2),
    so they are always strictly smaller — meaning larger per-km penalties and harder
    scoring — than the world scope. The floor of 1.0 m only guards against
    division-by-zero for micro-territories; it never affects normal countries.
    """
    if country_code:
        country_area_km2 = _load_country_areas_by_code().get(country_code)
        if country_area_km2:
            scale = MIN_REFERENCE_DISTANCE_METERS * max(0.5, (country_area_km2 / EARTH_AREA_KM2) ** 0.25) # After testing. Gives a more balanced scoring curve
            return max(1.0, scale)
    return MIN_REFERENCE_DISTANCE_METERS


def get_scope_scale_meters(scope: dict[str, Any]) -> float:
    """
    Return the scale of a scope in meters.
    """
    country_code = _clean_str(scope.get("country_code")).upper()
    continent_code = _clean_str(scope.get("continent_code")).upper()
    return _get_scope_scale_meters_cached(country_code, continent_code)


def compute_geoguessr_score(distance_km: float, scale_meters: float) -> int:
    """
    Compute the score using the original exponential curve, with the scope
    scale applied linearly to the distance term.
    """
    safe_distance_km = max(0.0, float(distance_km))
    effective_scale_meters = max(1.0, float(scale_meters))
    raw_score = MAX_ROUND_SCORE * pow(
        ROUNDING_TARGET_RATIO,
        (safe_distance_km * 1000.0) / effective_scale_meters,
    )
    return int(raw_score + 0.5)


def select_random_round_image(round_scope: dict[str, Any]) -> dict[str, Any] | None:
    conditions = [
        "o.latitude IS NOT NULL",
        "o.longitude IS NOT NULL",
    ]
    params: list[Any] = []

    country_code = _clean_str(round_scope.get("country_code")).upper()
    continent_code = _clean_str(round_scope.get("continent_code")).upper()
    if country_code:
        conditions.append("UPPER(o.country_code) = ?")
        params.append(country_code)
    elif continent_code:
        conditions.append("UPPER(o.continent_code) = ?")
        params.append(continent_code)

    conn = get_local_db()
    max_rowid_row = conn.execute("SELECT MAX(rowid) AS max_rowid FROM occurrences").fetchone()
    max_rowid = int(max_rowid_row["max_rowid"] or 0)
    if max_rowid <= 0:
        return None

    pivot_rowid = random.randint(1, max_rowid)

    def _pick_row(rowid_operator: str) -> Any:
        return conn.execute(
            f"""
            SELECT
                o.gbifID AS gbif_id,
                o.species AS species,
                s.scientific_name AS scientific_name,
                s.common_name_en AS vernacular_name,
                o.latitude AS latitude,
                o.longitude AS longitude,
                UPPER(o.country_code) AS country_code,
                o.country AS country,
                UPPER(o.continent_code) AS continent_code,
                o.continent AS continent,
                (
                    SELECT i.url
                    FROM images i
                    WHERE i.gbifID = o.gbifID
                    ORDER BY i.rowid DESC
                    LIMIT 1
                ) AS image_url
            FROM occurrences o
            LEFT JOIN species s ON s.species = o.species
            WHERE {" AND ".join(conditions)}
              AND o.rowid {rowid_operator} ?
            ORDER BY o.rowid
            LIMIT 1
            """,
            [*params, pivot_rowid],
        ).fetchone()

    row = _pick_row(">=")
    if not row:
        row = _pick_row("<")
    if not row:
        return None

    country_code = _clean_str(row["country_code"]).upper()
    continent_code = _clean_str(row["continent_code"]).upper()
    country_name = _clean_str(row["country"]) or _clean_str(get_country_name_by_code(country_code))
    continent_name = _clean_str(row["continent"]) or _clean_str(
        get_continent_name_by_code(continent_code)
    )

    scientific_name = _clean_str(row["scientific_name"]) or _clean_str(row["species"])
    vernacular_name = _format_vernacular_name(
        _clean_str(row["vernacular_name"]),
        scientific_name,
    )

    return {
        "gbif_id": int(row["gbif_id"]),
        "species": _clean_str(row["species"]),
        "scientific_name": scientific_name,
        "vernacular_name": vernacular_name,
        "latitude": float(row["latitude"]),
        "longitude": float(row["longitude"]),
        "country_code": country_code,
        "country": country_name or "Unknown country",
        "continent_code": continent_code,
        "continent": continent_name or "Unknown continent",
        "image_url": _clean_str(row["image_url"]),
    }


def get_scope_label(scope: dict[str, str]) -> str:
    scope_type = scope.get("scope_type")
    if scope_type == COUNTRY_SCOPE:
        country_name = scope.get("country") or scope.get("country_code") or "Country"
        return f"Scope: {country_name}"
    if scope_type == CONTINENT_SCOPE:
        continent_name = scope.get("continent") or scope.get("continent_code") or "Continent"
        return f"Scope: {continent_name}"
    return "Scope: World"
