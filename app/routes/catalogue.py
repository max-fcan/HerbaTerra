from flask import Blueprint, abort, current_app, render_template, request, url_for

from app.db.connections import get_replica_status, is_replica_ready
from app.services.catalogue import (
    get_catalogue_page,
    get_filter_options,
    parse_catalogue_filters,
    get_species_detail,
)
from app.services.geocoding import get_country_code_a2_by_code

bp = Blueprint("catalogue", __name__, url_prefix="/catalogue")


@bp.get("/", strict_slashes=False)
def catalogue():
    if not is_replica_ready():
        return render_template("db_loading.html", replica_status=get_replica_status()), 503
    active_filters = parse_catalogue_filters(request.args)
    catalogue_data = get_catalogue_page(active_filters)
    filter_options = get_filter_options()
    return render_template(
        "catalogue.html",
        catalogue=catalogue_data,
        filters=filter_options,
        active_filters=active_filters,
    )


@bp.get("/species/<path:species_name>") # Avec l'aide de l'IA, permet d'avoir une infinité de routes pour les espèces, sans avoir à les définir une par une. Le nom de l'espèce est passé en paramètre dans l'URL, et la fonction catalogue_species s'occupe de récupérer les données correspondantes et d'afficher la page de détail de l'espèce.
def catalogue_species(species_name: str):
    if not is_replica_ready():
        return render_template("db_loading.html", replica_status=get_replica_status()), 503
    species_detail = get_species_detail(
        species_name,
        initial_limit=25,
        include_country_map_stats=False,
    )
    if species_detail is None:
        abort(404)

    selected_geojson_file = current_app.config["MAP_GEOJSON_FILE"]
    try:
        country_code_a2_by_iso_code = get_country_code_a2_by_code()
    except FileNotFoundError:
        current_app.logger.warning(
            "ISO3166 CSV not found; country code normalization disabled for species map."
        )
        country_code_a2_by_iso_code = {}

    return render_template(
        "catalogue_species.html",
        species=species_detail,
        images_api_url=url_for(
            "api.catalogue_species_images_api", species_name=species_name
        ),
        map_stats_api_url=url_for(
            "api.catalogue_species_map_stats_api", species_name=species_name
        ),
        geojson_url=url_for("geo.geojson_file", filename=selected_geojson_file),
        country_code_a2_by_iso_code=country_code_a2_by_iso_code,
    )
