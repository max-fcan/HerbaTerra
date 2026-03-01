from __future__ import annotations

import math
from functools import lru_cache
from typing import Any

from app.db.connections import get_local_db
from app.services.geocoding import (
    get_continent_code_by_name,
    get_continent_name_by_code,
    get_continent_names_by_iso,
    get_country_code_a2_by_code,
    get_country_name_by_code,
)

ALLOWED_SORTS = {"popular", "media", "alpha"}
ALLOWED_PER_PAGE = {10, 25, 50}
TOP_LOCATIONS_LIMIT = 16


def _safe_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _clean_str(value: Any) -> str:
    return "" if value is None else str(value).strip()


def _clean_filter_value(value: Any, all_tokens: set[str] | None = None) -> str:
    cleaned = _clean_str(value)
    if all_tokens and cleaned.lower() in all_tokens:
        return ""
    return cleaned


def _convert_to_medium_image(url: str | None) -> str | None:
    return None if not url else url.replace("/original", "/medium")


@lru_cache(maxsize=1024) # Cache ajouté par l'IA
def _continent_code_for_country_code(country_code: str) -> str:
    """
    Fonction utilitaire pour obtenir le code de continent à partir d'un code de pays.
    """
    normalized_country_code = _clean_str(country_code).upper()
    if not normalized_country_code:
        return ""
    continent_name = get_continent_names_by_iso().get(normalized_country_code, "")
    return (get_continent_code_by_name(continent_name) or "").upper()


@lru_cache(maxsize=16) # Cache rajouté par l'IA
def _country_codes_for_continent(continent_code: str) -> tuple[str, ...]:
    """
    Fonction utilitaire, implémentée par l'IA, pour obtenir la liste des codes de pays appartenant à un continent donné.
    """
    normalized_continent_code = _clean_str(continent_code).upper()
    if not normalized_continent_code:
        return tuple()

    continent_name = get_continent_name_by_code(normalized_continent_code)
    if not continent_name:
        return tuple()

    return tuple(
        sorted(
            {
                _clean_str(country_code).upper()
                for country_code, mapped_continent_name in get_continent_names_by_iso().items()
                if mapped_continent_name == continent_name and _clean_str(country_code)
            }
        )
    )


def _execute(sql: str, params: list[Any] | tuple[Any, ...] | None = None) -> Any:
    """Fonction utilitaire pour exécuter une requête SQL avec des paramètres donnés."""
    return get_local_db().execute(sql, params or [])


def _query_dicts(
    sql: str, params: list[Any] | tuple[Any, ...] | None = None
) -> list[dict[str, Any]]:
    """Fonction utilitaire pour exécuter une requête SQL et retourner les résultats sous forme de liste de dictionnaires."""
    return [dict(row) for row in _execute(sql, params).fetchall()]


def _query_one_dict(
    sql: str, params: list[Any] | tuple[Any, ...] | None = None
) -> dict[str, Any] | None:
    """Fonction utilitaire pour exécuter une requête SQL et retourner le premier résultat sous forme de dictionnaire."""
    row = _execute(sql, params).fetchone()
    return dict(row) if row else None


def _build_species_where_clause(filters: dict[str, Any]) -> tuple[str, list[Any]]:
    """
    Faite par l'IA. Construire la clause WHERE de la requête SQL pour filtrer les espèces en fonction des filtres donnés. Retourne la clause WHERE et la liste des paramètres correspondants.
    """
    conditions: list[str] = []
    params: list[Any] = []

    q = filters.get("q") or ""
    if q:
        like = f"%{q.lower()}%"
        conditions.append(
            "("
            "LOWER(s.species) LIKE ? OR "
            "LOWER(s.scientific_name) LIKE ? OR "
            "LOWER(s.common_name_en) LIKE ? OR "
            "LOWER(s.family) LIKE ? OR "
            "LOWER(s.genus) LIKE ?"
            ")"
        )
        params.extend([like, like, like, like, like])

    family = filters.get("family") or ""
    if family:
        conditions.append("s.family = ? COLLATE NOCASE")
        params.append(family)

    genus = filters.get("genus") or ""
    if genus:
        conditions.append("s.genus = ? COLLATE NOCASE")
        params.append(genus)

    country_code = filters.get("country_code") or ""
    if country_code:
        conditions.append(
            """
            EXISTS (
                SELECT 1
                FROM species_country_stats scs
                WHERE scs.species = s.species
                  AND scs.country_code = ?
            )
            """
        )
        params.append(country_code)

    continent_code = filters.get("continent_code") or ""
    if continent_code:
        country_codes_in_continent = _country_codes_for_continent(continent_code)
        if not country_codes_in_continent:
            conditions.append("1 = 0")
        else:
            placeholders = ", ".join("?" for _ in country_codes_in_continent)
            conditions.append(
                f"""
                EXISTS (
                    SELECT 1
                    FROM species_country_stats scs
                    WHERE scs.species = s.species
                      AND scs.country_code IN ({placeholders})
                )
                """
            )
            params.extend(country_codes_in_continent)

    where_sql = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    return where_sql, params


def _get_sort_sql(sort_key: str, alias: str = "s") -> str:
    """Fonction utilitaire pour obtenir la clause ORDER BY d'après la clé de tri donnée."""
    prefix = f"{alias}." if alias else ""
    if sort_key == "media":
        return f"{prefix}image_count DESC, {prefix}species ASC"
    if sort_key == "alpha":
        return f"{prefix}species ASC"
    return f"{prefix}occurrence_count DESC, {prefix}species ASC"


def parse_catalogue_filters(args: Any) -> dict[str, Any]:
    """Fonction utilitaire pour parser les filtres de la page de catalogue à partir des arguments de requête. Nettoie les valeurs, applique les valeurs par défaut, et valide les options."""
    q = _clean_str(args.get("q"))
    family = _clean_filter_value(args.get("family"), {"all", "all families"})
    genus = _clean_filter_value(args.get("genus"), {"all", "all genera"})

    country_code = _clean_filter_value(
        args.get("country_code"),
        {"all", "all countries"},
    ).upper()

    continent_code = _clean_filter_value(
        args.get("continent_code"),
        {"all", "all continents"},
    ).upper()
    if not continent_code:
        continent_code = (
            get_continent_code_by_name(_clean_str(args.get("continent"))) or ""
        ).upper()

    if country_code and not get_country_name_by_code(country_code):
        country_code = ""
    if continent_code and not get_continent_name_by_code(continent_code):
        continent_code = ""

    sort = _clean_str(args.get("sort")) or "popular"
    if sort not in ALLOWED_SORTS:
        sort = "popular"

    per_page = _safe_int(args.get("per_page"), 25)
    if per_page not in ALLOWED_PER_PAGE:
        per_page = 25

    return {
        "q": q,
        "family": family,
        "genus": genus,
        "country_code": country_code,
        "country": get_country_name_by_code(country_code) if country_code else "",
        "continent_code": continent_code,
        "continent": get_continent_name_by_code(continent_code) if continent_code else "",
        "sort": sort,
        "page": max(1, _safe_int(args.get("page"), 1)),
        "per_page": per_page,
    }


@lru_cache(maxsize=1) # Cache ajouté par l'IA
def _get_filter_options_cached() -> dict[str, list[dict[str, str]]]:
    """Fonction utilitaire pour obtenir les options de filtre mises en cache."""
    family_rows = _query_dicts(
        """
        SELECT DISTINCT family
        FROM species
        WHERE family IS NOT NULL AND TRIM(family) <> ''
        ORDER BY family
        """
    )
    genus_rows = _query_dicts(
        """
        SELECT DISTINCT genus
        FROM species
        WHERE genus IS NOT NULL AND TRIM(genus) <> ''
        ORDER BY genus
        """
    )
    country_rows = _query_dicts(
        """
        SELECT DISTINCT country_code
        FROM species_country_stats
        WHERE country_code IS NOT NULL AND TRIM(country_code) <> ''
        """
    )
    country_code_map = get_country_code_a2_by_code()
    country_codes = sorted(
        {
            country_code_map.get(str(row.get("country_code", "")).strip().upper(), "")
            or str(row.get("country_code", "")).strip().upper()
            for row in country_rows
            if str(row.get("country_code", "")).strip()
        },
        key=lambda code: ((get_country_name_by_code(code) or code), code),
    )
    continent_codes = sorted(
        {
            _continent_code_for_country_code(code)
            for code in country_codes
            if _continent_code_for_country_code(code)
        },
        key=lambda code: ((get_continent_name_by_code(code) or code), code),
    )

    return {
        "family_options": [{"value": row["family"], "label": row["family"]} for row in family_rows],
        "genus_options": [{"value": row["genus"], "label": row["genus"]} for row in genus_rows],
        "country_options": [
            {"value": code, "label": f"{(get_country_name_by_code(code) or code)} ({code})"}
            for code in country_codes
        ],
        "continent_options": [
            {
                "value": code,
                "label": f"{(get_continent_name_by_code(code) or code)} ({code})",
            }
            for code in continent_codes
        ],
    }


def get_filter_options() -> dict[str, list[dict[str, str]]]:
    """Fonction utilitaire pour obtenir les options de filtre mises en cache."""
    cached = _get_filter_options_cached()
    return {key: [dict(option) for option in options] for key, options in cached.items()}


def _build_catalogue_page(filters: dict[str, Any]) -> dict[str, Any]:
    """Fonction principale pour construire les données de la page de catalogue en fonction des filtres donnés. Exécute les requêtes SQL nécessaires pour récupérer les espèces filtrées, les compteurs, et les échantillons de pays et d'images."""
    where_sql, where_params = _build_species_where_clause(filters)

    count_row = _query_one_dict(
        f"""
        SELECT COUNT(*) AS total_species
        FROM species s
        {where_sql}
        """,
        where_params,
    )
    total_species = int((count_row or {}).get("total_species") or 0)
    per_page = int(filters["per_page"])
    total_pages = max(1, math.ceil(total_species / per_page)) if total_species > 0 else 1
    page = min(int(filters["page"]), total_pages)
    sort_sql = _get_sort_sql(filters["sort"], alias="s")

    page_rows = _query_dicts(
        f"""
        SELECT
            s.species,
            s.scientific_name,
            s.common_name_en,
            s.family,
            s.genus,
            s.occurrence_count,
            s.country_count,
            s.image_count,
            (
                SELECT scs.country_code
                FROM species_country_stats scs
                WHERE scs.species = s.species
                ORDER BY scs.n DESC, scs.country_code ASC
                LIMIT 1
            ) AS sample_country_code,
            (
                SELECT NULLIF(TRIM(o.country), '')
                FROM occurrences o
                WHERE o.species = s.species
                ORDER BY o.gbifID DESC
                LIMIT 1
            ) AS sample_country,
            (
                SELECT i.url
                FROM occurrences o
                JOIN images i ON i.gbifID = o.gbifID
                WHERE o.species = s.species
                ORDER BY o.gbifID DESC, i.rowid DESC
                LIMIT 1
            ) AS image_url
        FROM species s
        {where_sql}
        ORDER BY {sort_sql}
        LIMIT ? OFFSET ?
        """,
        [*where_params, per_page, (page - 1) * per_page],
    )

    species_items: list[dict[str, Any]] = []
    for row in page_rows:
        sample_country_code = _clean_str(row.get("sample_country_code")).upper()
        sample_continent_code = _continent_code_for_country_code(sample_country_code)

        species_items.append(
            {
                "species": row.get("species"),
                "scientific_name": row.get("scientific_name") or row.get("species"),
                "common_name_en": (row.get("common_name_en") or "").strip().title(),
                "family": row.get("family"),
                "genus": row.get("genus"),
                "occurrence_count": int(row.get("occurrence_count") or 0),
                "country_count": int(row.get("country_count") or 0),
                "image_count": int(row.get("image_count") or 0),
                "sample_country": (
                    _clean_str(row.get("sample_country"))
                    or get_country_name_by_code(sample_country_code)
                    or "Unknown country"
                ),
                "sample_country_code": sample_country_code or "",
                "sample_continent": (
                    get_continent_name_by_code(sample_continent_code) or "Unknown continent"
                ),
                "sample_continent_code": sample_continent_code or "",
                "image_url": _convert_to_medium_image(row.get("image_url")),
            }
        )

    return {
        "species_list": species_items,
        "total_species": total_species,
        "page": page,
        "per_page": per_page,
        "total_pages": total_pages,
        "sort": filters["sort"],
    }


def _is_default_catalogue_filters(filters: dict[str, Any]) -> bool:
    """Fonction utilitaire pour vérifier si les filtres donnés sont les filtres par défaut (aucun filtre)."""
    return (
        (filters.get("q") or "") == ""
        and (filters.get("family") or "") == ""
        and (filters.get("genus") or "") == ""
        and (filters.get("country_code") or "") == ""
        and (filters.get("continent_code") or "") == ""
        and (filters.get("sort") or "popular") == "popular"
        and int(filters.get("page") or 1) == 1
        and int(filters.get("per_page") or 25) == 25
    )


@lru_cache(maxsize=1)
def _get_default_catalogue_page_cached() -> dict[str, Any]:
    """
    Implementé par l'IA.
    Mettre en cache la page de catalogue par défaut (sans filtres) pour accélérer le chargement de la page d'accueil et de la page de catalogue sans filtres.
    """
    return _build_catalogue_page(
        {
            "q": "",
            "family": "",
            "genus": "",
            "country_code": "",
            "country": "",
            "continent_code": "",
            "continent": "",
            "sort": "popular",
            "page": 1,
            "per_page": 25,
        }
    )


def get_catalogue_page(filters: dict[str, Any]) -> dict[str, Any]:
    """
    Implementé par l'IA.
    Récupérer les données de la page de catalogue en fonction des filtres. Si les filtres sont les filtres par défaut (aucun filtre), utiliser la version mise en cache de la page pour accélérer le chargement.
    """
    if not _is_default_catalogue_filters(filters):
        return _build_catalogue_page(filters)

    cached = _get_default_catalogue_page_cached()
    return {**cached, "species_list": [dict(item) for item in cached["species_list"]]}


def get_species_images_page(
    species_name: str,
    cursor_gbifid: int | None = None,
    cursor_rowid: int | None = None,
    country_code: str | None = None,
    continent_code: str | None = None,
    limit: int = 25,
) -> dict[str, Any]:
    """Fonction principale pour récupérer les données de la page d'images d'une espèce donnée."""
    page_limit = max(1, min(limit, 25))
    params: list[Any] = [species_name]
    conditions: list[str] = []

    normalized_country_code = _clean_str(country_code).upper()
    if normalized_country_code:
        conditions.append("o.country_code = ?")
        params.append(normalized_country_code)

    normalized_continent_code = _clean_str(continent_code).upper()
    if normalized_continent_code:
        conditions.append("o.continent_code = ?")
        params.append(normalized_continent_code)

    # Pagination basée sur le couple (gbifID, rowid) pour garantir un ordre stable et afficher les images les plus récentes en premier (généralement plus belles). 
    if cursor_gbifid is not None and cursor_rowid is not None:
        conditions.append("(o.gbifID < ? OR (o.gbifID = ? AND i.rowid < ?))")
        params.extend([cursor_gbifid, cursor_gbifid, cursor_rowid])
    elif cursor_gbifid is not None:
        conditions.append("o.gbifID < ?")
        params.append(cursor_gbifid)
    elif cursor_rowid is not None:
        conditions.append("i.rowid < ?")
        params.append(cursor_rowid)

    # Construire la clause WHERE en fonction de toutes les conditions
    where_tail = "".join(f" AND {condition}" for condition in conditions)
    rows = _query_dicts(
        f"""
        SELECT
            o.gbifID AS gbifID,
            i.rowid AS rowid,
            i.url AS url_original,
            i.license AS license,
            i.creator AS creator,
            o.country AS country,
            o.country_code AS country_code,
            o.continent AS continent,
            o.continent_code AS continent_code,
            o.state_province AS state_province,
            o.year AS year,
            o.month AS month
        FROM occurrences o
        JOIN images i ON i.gbifID = o.gbifID
        WHERE o.species = ?
          {where_tail}
        ORDER BY o.gbifID DESC, i.rowid DESC
        LIMIT ?
        """,
        [*params, page_limit + 1],
    )

    # Pagination
    has_more = len(rows) > page_limit
    page_rows = rows[:page_limit] if has_more else rows
    items = [
        {
            "gbifID": _safe_int(row.get("gbifID"), -1),
            "rowid": _safe_int(row.get("rowid"), -1),
            "url_original": row.get("url_original"),
            "url_medium": _convert_to_medium_image(row.get("url_original")),
            "license": row.get("license"),
            "creator": row.get("creator"),
            "country": row.get("country"),
            "country_code": row.get("country_code"),
            "continent": row.get("continent"),
            "continent_code": row.get("continent_code"),
            "state_province": row.get("state_province"),
            "year": row.get("year"),
            "month": row.get("month"),
        }
        for row in page_rows
    ]

    # Déterminer les curseurs pour la page suivante à partir du dernier élément de la page.
    next_cursor_gbifid: int | None = None
    next_cursor_rowid: int | None = None
    if has_more and items:
        last_item = items[-1]
        next_cursor_gbifid = _safe_int(last_item.get("gbifID"), -1)
        next_cursor_rowid = _safe_int(last_item.get("rowid"), -1)

    return {
        "items": items,
        "next_cursor_gbifid": next_cursor_gbifid,
        "next_cursor_rowid": next_cursor_rowid,
        "has_more": has_more,
    }


def _map_location_stats(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "country_code": str(row.get("country_code") or "").strip().upper(),
            "country": row.get("country") or "Unknown country",
            "continent_code": str(row.get("continent_code") or "").strip().upper(),
            "continent": row.get("continent") or "",
            "occurrence_count": int(row.get("occurrence_count") or 0),
            "image_count": int(row.get("image_count") or 0),
        }
        for row in rows
    ]


def _get_species_location_stats(species_name: str) -> list[dict[str, Any]]:
    rows = _query_dicts(
        """
        WITH country_meta AS (
            SELECT
                o.country_code AS country_code,
                COALESCE(NULLIF(TRIM(MAX(o.country)), ''), 'Unknown country') AS country,
                COALESCE(NULLIF(TRIM(MAX(o.continent_code)), ''), '') AS continent_code,
                COALESCE(NULLIF(TRIM(MAX(o.continent)), ''), '') AS continent
            FROM occurrences o
            WHERE o.species = ?
            GROUP BY o.country_code
        ),
        image_counts AS (
            SELECT
                o.country_code AS country_code,
                COUNT(i.rowid) AS image_count
            FROM occurrences o
            JOIN images i ON i.gbifID = o.gbifID
            WHERE o.species = ?
            GROUP BY o.country_code
        )
        SELECT
            scs.country_code AS country_code,
            COALESCE(cm.country, 'Unknown country') AS country,
            COALESCE(cm.continent_code, '') AS continent_code,
            COALESCE(cm.continent, '') AS continent,
            scs.n AS occurrence_count,
            COALESCE(ic.image_count, 0) AS image_count
        FROM species_country_stats scs
        LEFT JOIN country_meta cm ON cm.country_code = scs.country_code
        LEFT JOIN image_counts ic ON ic.country_code = scs.country_code
        WHERE scs.species = ?
        ORDER BY scs.n DESC, country ASC, continent ASC
        """,
        [species_name, species_name, species_name],
    )
    if rows:
        return _map_location_stats(rows)

    # Fallback when species_country_stats is empty for a species.
    fallback_rows = _query_dicts(
        """
        SELECT
            UPPER(COALESCE(o.country_code, '')) AS country_code,
            COALESCE(NULLIF(TRIM(MAX(o.country)), ''), 'Unknown country') AS country,
            UPPER(COALESCE(MAX(o.continent_code), '')) AS continent_code,
            COALESCE(NULLIF(TRIM(MAX(o.continent)), ''), '') AS continent,
            COUNT(DISTINCT o.gbifID) AS occurrence_count,
            COUNT(i.rowid) AS image_count
        FROM occurrences o
        LEFT JOIN images i ON i.gbifID = o.gbifID
        WHERE o.species = ?
        GROUP BY UPPER(COALESCE(o.country_code, '')), UPPER(COALESCE(o.continent_code, ''))
        ORDER BY occurrence_count DESC, country ASC, continent ASC
        """,
        [species_name],
    )
    return _map_location_stats(fallback_rows)


def _build_country_map_stats_from_location_stats(
    location_stats: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    aggregated: dict[str, dict[str, Any]] = {}
    for entry in location_stats:
        country_code = str(entry.get("country_code") or "").strip().upper()
        if not country_code:
            continue

        target = aggregated.setdefault(
            country_code,
            {
                "country_code": country_code,
                "country": str(entry.get("country") or "").strip() or "Unknown country",
                "occurrence_count": 0,
                "image_count": 0,
            },
        )
        target["occurrence_count"] += int(entry.get("occurrence_count") or 0)
        target["image_count"] += int(entry.get("image_count") or 0)

    return sorted(
        aggregated.values(),
        key=lambda item: (-int(item["occurrence_count"]), str(item["country"]).lower()),
    )


def get_species_location_summary(
    species_name: str,
    top_locations_limit: int | None = TOP_LOCATIONS_LIMIT,
) -> dict[str, list[dict[str, Any]]]:
    location_stats = _get_species_location_stats(species_name)
    top_limit = len(location_stats) if top_locations_limit is None else max(0, int(top_locations_limit))
    top_locations = [
        {
            "country_code": row.get("country_code"),
            "country": row.get("country"),
            "continent_code": row.get("continent_code"),
            "continent": row.get("continent"),
            "occurrence_count": int(row.get("occurrence_count") or 0),
        }
        for row in location_stats
        if str(row.get("country_code") or "").strip()
    ][:top_limit]

    return {
        "top_locations": top_locations,
        "country_map_stats": _build_country_map_stats_from_location_stats(location_stats),
    }


def get_species_country_map_stats(species_name: str) -> list[dict[str, Any]]:
    return get_species_location_summary(species_name)["country_map_stats"]


def get_species_detail(
    species_name: str,
    initial_limit: int = 25,
    include_country_map_stats: bool = True,
) -> dict[str, Any] | None:
    """Fonction simple, qui récupère les détails d'une espèce donnée, y compris les statistiques d'occurrence, les pays et continents où elle est présente, et un échantillon d'images. Utilisée pour construire la page détaillée d'une espèce."""
    species_row = _query_one_dict(
        """
        SELECT
            species,
            scientific_name,
            common_name_en,
            family,
            genus,
            occurrence_count,
            country_count,
            image_count
        FROM species
        WHERE species = ?
        LIMIT 1
        """,
        [species_name],
    )
    if not species_row:
        return None

    location_stats = _get_species_location_stats(species_name)
    continents = [
        continent_name
        for continent_name in dict.fromkeys(
            _clean_str(row.get("continent"))
            for row in location_stats
            if _clean_str(row.get("continent"))
        )
    ]
    top_locations = [
        {
            "country_code": row.get("country_code"),
            "country": row.get("country"),
            "continent_code": row.get("continent_code"),
            "continent": row.get("continent"),
            "occurrence_count": int(row.get("occurrence_count") or 0),
        }
        for row in location_stats
        if str(row.get("country_code") or "").strip()
    ]

    return {
        "species": species_row.get("species"),
        "scientific_name": species_row.get("scientific_name") or species_row.get("species"),
        "common_name_en": (species_row.get("common_name_en") or "").strip().title(),
        "family": species_row.get("family"),
        "genus": species_row.get("genus"),
        "occurrence_count": int(species_row.get("occurrence_count") or 0),
        "country_count": int(species_row.get("country_count") or 0),
        "image_count": int(species_row.get("image_count") or 0),
        "continents": continents,
        "top_locations": top_locations,
        "country_map_stats": (
            _build_country_map_stats_from_location_stats(location_stats)
            if include_country_map_stats
            else []
        ),
        "initial_images": get_species_images_page(species_name=species_name, limit=initial_limit),
    }
