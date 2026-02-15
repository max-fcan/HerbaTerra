"""Catalogue API — autocomplete, pagination, and dynamic filter endpoints."""

from flask import jsonify, request

from app.api import api_bp


@api_bp.route("/catalogue/autocomplete")
def catalogue_autocomplete():
    """JSON autocomplete for the catalogue search bar."""
    from app.services.catalogue import autocomplete_search

    q = request.args.get("q", "", type=str)
    return jsonify(autocomplete_search(q))


@api_bp.route("/catalogue/page")
def catalogue_page():
    """Paginated species data for infinite-scroll / AJAX loading."""
    from app.services.catalogue import get_species_catalogue

    page = request.args.get("page", 1, type=int)
    per_page = max(12, min(96, request.args.get("per_page", 24, type=int)))

    data = get_species_catalogue(
        page=page,
        per_page=per_page,
        search=request.args.get("q", None, type=str),
        family=request.args.get("family", None, type=str),
        genus=request.args.get("genus", None, type=str),
        continent=request.args.get("continent", None, type=str),
        country=request.args.get("country", None, type=str),
    )

    return jsonify(
        {
            "species_list": data["species_list"],
            "page": data["page"],
            "total_pages": data["total_pages"],
        }
    )


@api_bp.route("/catalogue/filters")
def catalogue_filters():
    """Dynamic filter options matching the current search/filter criteria."""
    from app.services.catalogue import get_dynamic_filter_options

    filters = get_dynamic_filter_options(
        search=request.args.get("q", None, type=str),
        family=request.args.get("family", None, type=str),
        genus=request.args.get("genus", None, type=str),
        continent=request.args.get("continent", None, type=str),
        country=request.args.get("country", None, type=str),
    )
    return jsonify(filters)
