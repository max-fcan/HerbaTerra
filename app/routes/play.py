from flask import Blueprint, render_template, request, jsonify, abort

play_bp = Blueprint('play', __name__, url_prefix='/play')


@play_bp.route('')
@play_bp.route('/')
def index():
    """Play index page"""
    return render_template('play/index.html')


@play_bp.route('/daily')
def daily():
    """Daily challenge page"""
    return render_template('play/daily.html')


@play_bp.route('/game')
def game():
    """Game page"""
    return render_template('play/game.html')


@play_bp.route('/map')
def map():
    """Map page"""
    return render_template('play/map.html')


@play_bp.route('/tournaments')
def tournaments():
    """Tournaments page"""
    return render_template('play/tournaments.html')


@play_bp.route('/country')
def country():
    """Country detail page"""
    country_name = request.args.get('name', 'Unknown')
    country_code = request.args.get('code', '')
    return render_template('play/country.html',
                         country_name=country_name,
                         country_code=country_code)


# ── Catalogue ───────────────────────────────────────────────────────────────

@play_bp.route('/catalogue')
def catalogue():
    """Species catalogue — paginated grid of species cards."""
    from app.services.catalogue import get_species_catalogue, get_filter_options

    page = request.args.get('page', 1, type=int)
    search = request.args.get('q', None, type=str)
    family = request.args.get('family', None, type=str)
    genus = request.args.get('genus', None, type=str)
    continent = request.args.get('continent', None, type=str)
    country_filter = request.args.get('country', None, type=str)

    data = get_species_catalogue(
        page=page,
        per_page=24,
        search=search,
        family=family,
        genus=genus,
        continent=continent,
        country=country_filter,
    )
    filters = get_filter_options()

    return render_template(
        'play/catalogue.html',
        catalogue=data,
        filters=filters,
        active_filters={
            'q': search or '',
            'family': family or '',
            'genus': genus or '',
            'continent': continent or '',
            'country': country_filter or '',
        },
    )


@play_bp.route('/catalogue/species/<path:species_name>')
def species_detail(species_name: str):
    """Detailed view for a single species."""
    from app.services.catalogue import get_species_detail

    detail = get_species_detail(species_name)
    if detail is None:
        abort(404)
    return render_template('play/species_detail.html', species=detail)


@play_bp.route('/api/catalogue/autocomplete')
def catalogue_autocomplete():
    """JSON autocomplete endpoint for the catalogue search bar."""
    from app.services.catalogue import autocomplete_search

    q = request.args.get('q', '', type=str)
    results = autocomplete_search(q)
    return jsonify(results)


@play_bp.route('/catalogue/api/page')
def catalogue_page_api():
    """JSON API endpoint for infinite scroll pagination.
    
    Returns paginated catalogue data without HTML wrapper, 
    optimized for AJAX loading.
    """
    from app.services.catalogue import get_species_catalogue

    page = request.args.get('page', 1, type=int)
    search = request.args.get('q', None, type=str)
    family = request.args.get('family', None, type=str)
    genus = request.args.get('genus', None, type=str)
    continent = request.args.get('continent', None, type=str)
    country_filter = request.args.get('country', None, type=str)

    data = get_species_catalogue(
        page=page,
        per_page=24,
        search=search,
        family=family,
        genus=genus,
        continent=continent,
        country=country_filter,
    )
    
    # Return only data needed for AJAX, not full page
    return jsonify({
        'species_list': data['species_list'],
        'page': data['page'],
        'total_pages': data['total_pages'],
    })


@play_bp.route('/catalogue/api/filters')
def catalogue_filters_api():
    """JSON endpoint for dynamic filter options based on current filters.
    
    Returns available filter options that match the current search/filter criteria.
    """
    from app.services.catalogue import get_dynamic_filter_options

    search = request.args.get('q', None, type=str)
    family = request.args.get('family', None, type=str)
    genus = request.args.get('genus', None, type=str)
    continent = request.args.get('continent', None, type=str)
    country_filter = request.args.get('country', None, type=str)

    filters = get_dynamic_filter_options(
        search=search,
        family=family,
        genus=genus,
        continent=continent,
        country=country_filter,
    )
    return jsonify(filters)

    q = request.args.get('q', '', type=str)
    results = autocomplete_search(q, limit=12)
    return jsonify(results)