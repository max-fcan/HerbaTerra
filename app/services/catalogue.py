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


def _convert_to_medium_image(image_url: str | None) -> str | None:
    """Convert image URLs from 'original' to 'medium' size for better performance."""
    if not image_url:
        return image_url
    return image_url.replace('/original', '/medium')


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
            # Improved search logic: prioritize species, genus, family names
            # Use separate conditions for better performance and clarity
            search_lower = search.lower()
            conditions.append(
                "(LOWER(species) LIKE ? OR LOWER(genus) LIKE ? OR LOWER(family) LIKE ?)"
            )
            like = f"%{search_lower}%"
            params.extend([like, like, like])

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
        # Add relevance scoring when searching
        if search:
            # Order by relevance: exact match > starts with > contains
            search_lower = search.lower()
            data_sql = f"""
            WITH filtered AS (
                SELECT *,
                    CASE 
                        WHEN LOWER(species) = ? THEN 100
                        WHEN LOWER(species) LIKE ? THEN 90
                        WHEN LOWER(genus) = ? THEN 80
                        WHEN LOWER(genus) LIKE ? THEN 70
                        WHEN LOWER(family) = ? THEN 60
                        WHEN LOWER(family) LIKE ? THEN 50
                        ELSE 40
                    END as relevance_score
                FROM images WHERE {where}
            ),
            species_agg AS (
                SELECT
                    species,
                    FIRST(genus) AS genus,
                    FIRST(family) AS family,
                    MODE(country) AS country,
                    MODE(continent) AS continent,
                    MODE(admin1) AS admin1,
                    COUNT(*) AS observation_count,
                    MIN(eventDate) AS earliest_date,
                    MAX(eventDate) AS latest_date,
                    FIRST(image_url) AS image_url,
                    MAX(relevance_score) AS max_relevance
                FROM filtered
                GROUP BY species
                ORDER BY max_relevance DESC, species
                LIMIT ? OFFSET ?
            )
            SELECT species, genus, family, country, continent, admin1, 
                   observation_count, earliest_date, latest_date, image_url
            FROM species_agg
            """
            # Add search parameters for CASE statement
            starts_with = f"{search_lower}%"
            search_params = [search_lower, starts_with] * 3 + params + [per_page, (page - 1) * per_page]
        else:
            data_sql = f"""
            WITH filtered AS (
                SELECT * FROM images WHERE {where}
            ),
            species_agg AS (
                SELECT
                    species,
                    FIRST(genus) AS genus,
                    FIRST(family) AS family,
                    MODE(country) AS country,
                    MODE(continent) AS continent,
                    MODE(admin1) AS admin1,
                    COUNT(*) AS observation_count,
                    MIN(eventDate) AS earliest_date,
                    MAX(eventDate) AS latest_date,
                    FIRST(image_url) AS image_url
                FROM filtered
                GROUP BY species
                ORDER BY species
                LIMIT ? OFFSET ?
            )
            SELECT * FROM species_agg
            """
            search_params = params + [per_page, (page - 1) * per_page]
        
        rows = conn.execute(data_sql, search_params).fetchall()

        columns = [
            "species", "genus", "family", "country", "continent",
            "admin1", "observation_count", "earliest_date", "latest_date",
            "image_url",
        ]
        items = [dict(zip(columns, row)) for row in rows]

        # Format location string and optimize image URLs for each item
        for item in items:
            parts = [p for p in [item.get("admin1"), item.get("country"), item.get("continent")] if p]
            item["location"] = ", ".join(parts) if parts else "Unknown"
            # Format date nicely
            raw = item.get("latest_date") or item.get("earliest_date") or ""
            item["date_display"] = raw[:10] if raw else "Unknown"
            # Convert image URL to medium size
            item["image_url"] = _convert_to_medium_image(item.get("image_url"))

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
        
        # Convert all image URLs to medium size
        for obs in observations:
            obs["image_url"] = _convert_to_medium_image(obs.get("image_url"))

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


def get_dynamic_filter_options(
    search: str | None = None,
    family: str | None = None,
    genus: str | None = None,
    continent: str | None = None,
    country: str | None = None,
) -> Dict[str, List[str]]:
    """Return available filter options based on current filters.
    
    This ensures dropdowns only show options that would return results
    when combined with existing filters.
    """
    conn = _connect()
    try:
        # Build WHERE clauses for already-selected filters
        conditions: list[str] = ["species IS NOT NULL", "image_url IS NOT NULL"]
        params: list[Any] = []

        if search:
            # Use same improved search logic as catalogue
            search_lower = search.lower()
            conditions.append(
                "(LOWER(species) LIKE ? OR LOWER(genus) LIKE ? OR LOWER(family) LIKE ?)"
            )
            like = f"%{search_lower}%"
            params.extend([like, like, like])

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

        result: Dict[str, List[str]] = {}

        # For each filter field, get distinct values from filtered data
        for col in ("family", "genus", "continent", "country"):
            rows = conn.execute(
                f"SELECT DISTINCT {col} FROM images WHERE {where} AND {col} IS NOT NULL ORDER BY {col}",
                params
            ).fetchall()
            result[col + "_options"] = [r[0] for r in rows]

        return result
    finally:
        conn.close()


def autocomplete_search(query: str, limit: int = 10) -> List[Dict[str, str]]:
    """
    Fast autocomplete against species, genus, family, country, city.
    Returns a list of {value, label, type, score} suggestions prioritized by relevance.
    """
    if not query or len(query) < 2:
        return []

    conn = _connect()
    try:
        query_lower = query.lower()
        like_pattern = f"%{query_lower}%"
        starts_with_pattern = f"{query_lower}%"
        suggestions: list[Dict[str, Any]] = []

        # Species matches (highest priority)
        # Score: 100 for exact match, 90 for starts with, 80 for contains
        rows = conn.execute(
            """SELECT DISTINCT species, 
                   CASE 
                       WHEN LOWER(species) = ? THEN 100
                       WHEN LOWER(species) LIKE ? THEN 90
                       ELSE 80
                   END as score
               FROM images 
               WHERE LOWER(species) LIKE ? AND species IS NOT NULL 
               ORDER BY score DESC, species 
               LIMIT ?""",
            [query_lower, starts_with_pattern, like_pattern, limit],
        ).fetchall()
        suggestions.extend({"value": r[0], "label": r[0], "type": "species", "score": r[1]} for r in rows)

        # Family matches (medium-high priority)
        # Score: 70 for exact, 60 for starts with, 50 for contains
        rows = conn.execute(
            """SELECT DISTINCT family,
                   CASE 
                       WHEN LOWER(family) = ? THEN 70
                       WHEN LOWER(family) LIKE ? THEN 60
                       ELSE 50
                   END as score
               FROM images 
               WHERE LOWER(family) LIKE ? AND family IS NOT NULL 
               ORDER BY score DESC, family 
               LIMIT ?""",
            [query_lower, starts_with_pattern, like_pattern, limit // 2],
        ).fetchall()
        suggestions.extend({"value": r[0], "label": r[0], "type": "family", "score": r[1]} for r in rows)

        # Genus matches (medium priority)
        # Score: 65 for exact, 55 for starts with, 45 for contains
        rows = conn.execute(
            """SELECT DISTINCT genus,
                   CASE 
                       WHEN LOWER(genus) = ? THEN 65
                       WHEN LOWER(genus) LIKE ? THEN 55
                       ELSE 45
                   END as score
               FROM images 
               WHERE LOWER(genus) LIKE ? AND genus IS NOT NULL 
               ORDER BY score DESC, genus 
               LIMIT ?""",
            [query_lower, starts_with_pattern, like_pattern, limit // 2],
        ).fetchall()
        suggestions.extend({"value": r[0], "label": r[0], "type": "genus", "score": r[1]} for r in rows)

        # Country matches (lower priority)
        # Score: 40 for exact, 30 for starts with, 20 for contains
        rows = conn.execute(
            """SELECT DISTINCT country,
                   CASE 
                       WHEN LOWER(country) = ? THEN 40
                       WHEN LOWER(country) LIKE ? THEN 30
                       ELSE 20
                   END as score
               FROM images 
               WHERE LOWER(country) LIKE ? AND country IS NOT NULL 
               ORDER BY score DESC, country 
               LIMIT ?""",
            [query_lower, starts_with_pattern, like_pattern, limit // 3],
        ).fetchall()
        suggestions.extend({"value": r[0], "label": r[0], "type": "country", "score": r[1]} for r in rows)

        # Continent matches (lower priority)
        # Score: 35 for exact, 25 for starts with, 15 for contains
        rows = conn.execute(
            """SELECT DISTINCT continent,
                   CASE 
                       WHEN LOWER(continent) = ? THEN 35
                       WHEN LOWER(continent) LIKE ? THEN 25
                       ELSE 15
                   END as score
               FROM images 
               WHERE LOWER(continent) LIKE ? AND continent IS NOT NULL 
               ORDER BY score DESC, continent 
               LIMIT ?""",
            [query_lower, starts_with_pattern, like_pattern, limit // 4],
        ).fetchall()
        suggestions.extend({"value": r[0], "label": r[0], "type": "continent", "score": r[1]} for r in rows)

        # Sort by score (highest first), then alphabetically
        suggestions.sort(key=lambda x: (-x['score'], x['label']))
        
        # Deduplicate by value while preserving order
        seen = set()
        unique_suggestions = []
        for s in suggestions:
            if s['value'] not in seen:
                seen.add(s['value'])
                unique_suggestions.append(s)
        
        return unique_suggestions[:limit]
    finally:
        conn.close()
