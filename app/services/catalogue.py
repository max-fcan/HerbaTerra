"""
Catalogue service — efficient species-grouped queries against the DuckDB
plant-image database with location resolution, filtering, and pagination.
"""

from __future__ import annotations

import duckdb
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

DB_PATH = "data/gbif_plants.duckdb"


def _connect() -> duckdb.DuckDBPyConnection:
    return duckdb.connect(DB_PATH, read_only=True)


# ── Catalogue list (species cards) ──────────────────────────────────────────

def get_species_catalogue(
    *,
    page: int = 1,
    per_page: int = 24,
    search: str | None = None,
    family: str | None = None,
    genus: str | None = None,
    continent: str | None = None,
    country: str | None = None,
) -> Dict[str, Any]:
    """
    Return paginated, filterable list of species with one representative
    image per species and basic aggregated metadata.

    Each item contains:
      species, genus, family, image_url (cover), country (predominant),
      continent, observation_count, earliest/latest eventDate.
    """
    conn = _connect()
    try:
        # Build WHERE clauses dynamically
        conditions: list[str] = ["species IS NOT NULL", "image_url IS NOT NULL"]
        params: list[Any] = []

        if search:
            conditions.append(
                "(LOWER(species) LIKE ? OR LOWER(genus) LIKE ? OR LOWER(family) LIKE ? "
                "OR LOWER(country) LIKE ? OR LOWER(city) LIKE ?)"
            )
            like = f"%{search.lower()}%"
            params.extend([like, like, like, like, like])

        if family:
            conditions.append("LOWER(family) = LOWER(?)")
            params.append(family)

        if genus:
            conditions.append("LOWER(genus) = LOWER(?)")
            params.append(genus)

        if continent:
            conditions.append("LOWER(continent) = LOWER(?)")
            params.append(continent)

        if country:
            conditions.append("LOWER(country) = LOWER(?)")
            params.append(country)

        where = " AND ".join(conditions)

        # Count distinct species matching filters
        count_sql = f"SELECT COUNT(DISTINCT species) FROM images WHERE {where}"
        total_species = conn.execute(count_sql, params).fetchone()[0]

        # Paginated species list with aggregated info
        # For each species: pick a cover image, predominant country, counts, dates
        data_sql = f"""
        WITH filtered AS (
            SELECT * FROM images WHERE {where}
        ),
        species_agg AS (
            SELECT
                species,
                FIRST(genus) AS genus,
                FIRST(family) AS family,
                -- predominant country = most frequent
                MODE(country) AS country,
                MODE(continent) AS continent,
                MODE(admin1) AS admin1,
                COUNT(*) AS observation_count,
                MIN(eventDate) AS earliest_date,
                MAX(eventDate) AS latest_date,
                -- cover image: pick the first non-null image
                FIRST(image_url) AS image_url
            FROM filtered
            GROUP BY species
            ORDER BY species
            LIMIT ? OFFSET ?
        )
        SELECT * FROM species_agg
        """
        offset = (page - 1) * per_page
        rows = conn.execute(data_sql, params + [per_page, offset]).fetchall()

        columns = [
            "species", "genus", "family", "country", "continent",
            "admin1", "observation_count", "earliest_date", "latest_date",
            "image_url",
        ]
        items = [dict(zip(columns, row)) for row in rows]

        # Format location string for each item
        for item in items:
            parts = [p for p in [item.get("admin1"), item.get("country"), item.get("continent")] if p]
            item["location"] = ", ".join(parts) if parts else "Unknown"
            # Format date nicely
            raw = item.get("latest_date") or item.get("earliest_date") or ""
            item["date_display"] = raw[:10] if raw else "Unknown"

        total_pages = max(1, -(-total_species // per_page))  # ceil division

        return {
            "species_list": items,
            "page": page,
            "per_page": per_page,
            "total_species": total_species,
            "total_pages": total_pages,
        }
    finally:
        conn.close()


# ── Species detail ──────────────────────────────────────────────────────────

def get_species_detail(species_name: str) -> Dict[str, Any] | None:
    """
    Return full detail for a single species: all images, all locations, dates.
    """
    conn = _connect()
    try:
        sql = """
        SELECT
            image_url, lat, lon, country, continent, admin1, admin2, city,
            eventDate, year, genus, family, taxonRank, license, rightsHolder,
            occurrence_url
        FROM images
        WHERE species = ?
          AND image_url IS NOT NULL
        ORDER BY eventDate DESC
        """
        rows = conn.execute(sql, [species_name]).fetchall()
        if not rows:
            return None

        columns = [
            "image_url", "lat", "lon", "country", "continent", "admin1",
            "admin2", "city", "eventDate", "year", "genus", "family",
            "taxonRank", "license", "rightsHolder", "occurrence_url",
        ]
        observations = [dict(zip(columns, r)) for r in rows]

        # Aggregate info
        genus = observations[0]["genus"]
        family = observations[0]["family"]
        taxon_rank = observations[0]["taxonRank"]

        # Collect unique locations
        location_set: dict[str, int] = {}
        for obs in observations:
            parts = [p for p in [obs.get("city"), obs.get("admin2"), obs.get("admin1"), obs.get("country"), obs.get("continent")] if p]
            loc_str = ", ".join(parts) if parts else "Unknown"
            location_set[loc_str] = location_set.get(loc_str, 0) + 1
        # Sort by frequency descending
        locations_sorted = sorted(location_set.items(), key=lambda x: -x[1])

        # Unique images (deduplicate)
        seen_urls: set[str] = set()
        unique_images: list[dict] = []
        for obs in observations:
            url = obs["image_url"]
            if url not in seen_urls:
                seen_urls.add(url)
                unique_images.append(obs)

        # Date range
        dates = [o["eventDate"] for o in observations if o.get("eventDate")]
        earliest = min(dates)[:10] if dates else "Unknown"
        latest = max(dates)[:10] if dates else "Unknown"

        # Predominant country/continent
        countries = [o["country"] for o in observations if o.get("country")]
        continents = [o["continent"] for o in observations if o.get("continent")]

        return {
            "species": species_name,
            "genus": genus,
            "family": family,
            "taxon_rank": taxon_rank,
            "observation_count": len(observations),
            "image_count": len(unique_images),
            "images": unique_images,
            "locations": locations_sorted,
            "predominant_country": max(set(countries), key=countries.count) if countries else "Unknown",
            "predominant_continent": max(set(continents), key=continents.count) if continents else "Unknown",
            "earliest_date": earliest,
            "latest_date": latest,
        }
    finally:
        conn.close()


# ── Autocomplete / filter options ───────────────────────────────────────────

def get_filter_options() -> Dict[str, List[str]]:
    """Return distinct families, genera, continents, countries for filter dropdowns."""
    conn = _connect()
    try:
        result: Dict[str, List[str]] = {}
        for col in ("family", "genus", "continent", "country"):
            rows = conn.execute(
                f"SELECT DISTINCT {col} FROM images WHERE {col} IS NOT NULL ORDER BY {col}"
            ).fetchall()
            result[col + "_options"] = [r[0] for r in rows]
        return result
    finally:
        conn.close()


def autocomplete_search(query: str, limit: int = 10) -> List[Dict[str, str]]:
    """
    Fast autocomplete against species, genus, family, country, city.
    Returns a list of {value, label, type} suggestions.
    """
    if not query or len(query) < 2:
        return []

    conn = _connect()
    try:
        like = f"%{query.lower()}%"
        suggestions: list[Dict[str, str]] = []

        # Species matches
        rows = conn.execute(
            "SELECT DISTINCT species FROM images WHERE LOWER(species) LIKE ? AND species IS NOT NULL ORDER BY species LIMIT ?",
            [like, limit],
        ).fetchall()
        suggestions.extend({"value": r[0], "label": r[0], "type": "species"} for r in rows)

        # Family matches
        rows = conn.execute(
            "SELECT DISTINCT family FROM images WHERE LOWER(family) LIKE ? AND family IS NOT NULL ORDER BY family LIMIT ?",
            [like, limit // 2],
        ).fetchall()
        suggestions.extend({"value": r[0], "label": r[0], "type": "family"} for r in rows)

        # Genus matches
        rows = conn.execute(
            "SELECT DISTINCT genus FROM images WHERE LOWER(genus) LIKE ? AND genus IS NOT NULL ORDER BY genus LIMIT ?",
            [like, limit // 2],
        ).fetchall()
        suggestions.extend({"value": r[0], "label": r[0], "type": "genus"} for r in rows)

        # Country matches
        rows = conn.execute(
            "SELECT DISTINCT country FROM images WHERE LOWER(country) LIKE ? AND country IS NOT NULL ORDER BY country LIMIT ?",
            [like, limit // 2],
        ).fetchall()
        suggestions.extend({"value": r[0], "label": r[0], "type": "country"} for r in rows)

        # City matches
        rows = conn.execute(
            "SELECT DISTINCT city FROM images WHERE LOWER(city) LIKE ? AND city IS NOT NULL ORDER BY city LIMIT ?",
            [like, limit // 2],
        ).fetchall()
        suggestions.extend({"value": r[0], "label": r[0], "type": "location"} for r in rows)

        return suggestions[:limit * 2]
    finally:
        conn.close()
