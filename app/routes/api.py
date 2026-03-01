from flask import Blueprint, jsonify, request

from app.db.connections import get_replica_status, is_replica_ready
from app.services.catalogue import (
    get_filter_options,
    get_species_images_page,
    get_species_location_summary,
)

bp = Blueprint("api", __name__, url_prefix="/api")


@bp.get("/db/replica-status")
def replica_status_api():
    return jsonify(get_replica_status())


@bp.get("/catalogue/filter-options")
def catalogue_filter_options_api():
    if not is_replica_ready():
        return jsonify(get_replica_status()), 503
    return jsonify(get_filter_options())


@bp.get("/catalogue/species/<path:species_name>/images")
def catalogue_species_images_api(species_name: str):
    if not is_replica_ready():
        return jsonify(get_replica_status()), 503
    cursor_gbifid = request.args.get("cursor_gbifid", default=None, type=int)
    cursor_rowid = request.args.get("cursor_rowid", default=None, type=int)
    country_code = request.args.get("country_code", default="", type=str)
    continent_code = request.args.get("continent_code", default="", type=str)
    limit = request.args.get("limit", default=25, type=int)
    page = get_species_images_page(
        species_name=species_name,
        cursor_gbifid=cursor_gbifid,
        cursor_rowid=cursor_rowid,
        country_code=country_code,
        continent_code=continent_code,
        limit=limit,
    )
    return jsonify(page)


@bp.get("/catalogue/species/<path:species_name>/map-stats")
def catalogue_species_map_stats_api(species_name: str):
    if not is_replica_ready():
        return jsonify(get_replica_status()), 503
    summary = get_species_location_summary(species_name, top_locations_limit=None)
    return jsonify(
        {
            "items": summary["country_map_stats"],
            "country_map_stats": summary["country_map_stats"],
            "top_locations": summary["top_locations"],
        }
    )
