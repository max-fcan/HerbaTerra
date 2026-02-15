"""Catalogue blueprint — browseable species grid and species detail pages."""

from flask import Blueprint, render_template, request, abort, jsonify

catalogue_bp = Blueprint("catalogue", __name__, url_prefix="/catalogue")


@catalogue_bp.route("/")
def index():
    """Paginated, filterable species card grid."""
    from app.services.catalogue import get_species_catalogue, get_filter_options

    page = request.args.get("page", 1, type=int)
    per_page = max(12, min(96, request.args.get("per_page", 24, type=int)))

    search = request.args.get("q", None, type=str)
    family = request.args.get("family", None, type=str)
    genus = request.args.get("genus", None, type=str)
    continent = request.args.get("continent", None, type=str)
    country_filter = request.args.get("country", None, type=str)

    data = get_species_catalogue(
        page=page,
        per_page=per_page,
        search=search,
        family=family,
        genus=genus,
        continent=continent,
        country=country_filter,
    )
    filters = get_filter_options()

    return render_template(
        "catalogue/index.html",
        catalogue=data,
        filters=filters,
        active_filters={
            "q": search or "",
            "family": family or "",
            "genus": genus or "",
            "continent": continent or "",
            "country": country_filter or "",
        },
    )


@catalogue_bp.route("/species/<path:species_name>")
def species_detail(species_name: str):
    """Detailed view for a single species."""
    from app.services.catalogue import get_species_detail

    detail = get_species_detail(species_name)
    if detail is None:
        abort(404)
    return render_template("catalogue/species.html", species=detail)


@catalogue_bp.route("/api/autocomplete")
def autocomplete_api():
    """JSON autocomplete endpoint for catalogue search."""
    from app.services.catalogue import autocomplete_search

    q = request.args.get("q", "", type=str)
    results = autocomplete_search(q, limit=12)
    return jsonify(results)


@catalogue_bp.route("/api/page")
def page_api():
    """JSON endpoint for filtered catalogue page data (infinite scroll)."""
    from app.services.catalogue import get_species_catalogue

    page = request.args.get("page", 1, type=int)
    per_page = max(12, min(96, request.args.get("per_page", 24, type=int)))

    search = request.args.get("q", None, type=str)
    family = request.args.get("family", None, type=str)
    genus = request.args.get("genus", None, type=str)
    continent = request.args.get("continent", None, type=str)
    country_filter = request.args.get("country", None, type=str)

    data = get_species_catalogue(
        page=page,
        per_page=per_page,
        search=search,
        family=family,
        genus=genus,
        continent=continent,
        country=country_filter,
    )

    return jsonify(
        {
            "species_list": data["species_list"],
            "page": data["page"],
            "total_pages": data["total_pages"],
            "total_species": data["total_species"],
            "per_page": data["per_page"],
        }
    )


@catalogue_bp.route("/api/filters")
def filters_api():
    """JSON endpoint for dynamic filter options based on current filters."""
    from app.services.catalogue import get_dynamic_filter_options

    search = request.args.get("q", None, type=str)
    family = request.args.get("family", None, type=str)
    genus = request.args.get("genus", None, type=str)
    continent = request.args.get("continent", None, type=str)
    country_filter = request.args.get("country", None, type=str)

    filters = get_dynamic_filter_options(
        search=search,
        family=family,
        genus=genus,
        continent=continent,
        country=country_filter,
    )
    return jsonify(filters)
