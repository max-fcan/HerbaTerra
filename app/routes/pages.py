from flask import Blueprint, current_app, redirect, render_template, url_for

from app.db.connections import get_replica_status, is_replica_ready
from app.services.geocoding import (
    get_continent_code_by_name,
    get_continent_names_by_iso,
    get_country_code_a2_by_code,
)

bp = Blueprint("pages", __name__)


@bp.get("/")
def index():
    return render_template("index.html")


@bp.get("/start")
def start():
    if is_replica_ready():
        return redirect(url_for("pages.hub"))
    return render_template("db_loading.html", replica_status=get_replica_status())


@bp.get("/hub")
def hub():
    """Affiche la page centrale du site, avec la carte interactive et les hubs de recherche."""
    selected_geojson_file = current_app.config["MAP_GEOJSON_FILE"]
    try:
        continent_names_by_iso_code = get_continent_names_by_iso()
        country_code_a2_by_iso_code = get_country_code_a2_by_code()
    except FileNotFoundError:
        current_app.logger.warning(
            "ISO3166 CSV not found; continent labels disabled in hub popups."
        )
        continent_names_by_iso_code = {}
        country_code_a2_by_iso_code = {}

    continent_codes_by_name: dict[str, str] = {}
    for continent_name in set(continent_names_by_iso_code.values()):
        if not continent_name:
            continue
        code = get_continent_code_by_name(continent_name)
        if code:
            continent_codes_by_name[continent_name] = code

    return render_template(
        "hub.html",
        continent_names_by_iso_code=continent_names_by_iso_code,
        continent_codes_by_name=continent_codes_by_name,
        country_code_a2_by_iso_code=country_code_a2_by_iso_code,
        geojson_url=url_for("geo.geojson_file", filename=selected_geojson_file),
    )


@bp.get("/about")
def about():
    """Affiche la page 'À propos' du site. Contient des informations sur le projet, les sources de données, les crédits, etc."""
    return render_template("about.html")
