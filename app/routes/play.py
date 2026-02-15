from flask import Blueprint, render_template, request, jsonify, abort

play_bp = Blueprint('play', __name__, url_prefix='/play')

from app.services.challenges import Challenge



@play_bp.route('')
@play_bp.route('/')
def index():
    """Play index page"""
    return render_template('play/index.html')


@play_bp.route('/daily')
def daily():
    """Daily challenge page"""
    challenge = Challenge().to_dict()
    return render_template('play/daily_game_v7.html', challenge=challenge)


@play_bp.route('/daily/next')
def daily_next():
    """Return the next daily challenge as JSON."""
    challenge = Challenge()
    if not challenge.url:
        return jsonify({"challenge": None}), 404
    return jsonify({"challenge": challenge.to_dict()})


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


# ── Mapillary Integration ──────────────────────────────────────────────────

@play_bp.route('/api/mapillary/nearest')
def get_nearest_mapillary_image():
    """Find nearest Mapillary image to coordinates within 1km radius"""
    from app.services.mapillary_client import fetch_images_in_bbox
    
    lat = request.args.get('lat', type=float)
    lon = request.args.get('lon', type=float)
    radius = request.args.get('radius', 1000, type=int)
    
    if not lat or not lon:
        return jsonify({'error': 'lat and lon required'}), 400
    
    # Calculate bounding box
    lat_offset = radius / 111320
    lon_offset = radius / (111320 * abs(lat / 90) if lat != 0 else 1)
    
    images = fetch_images_in_bbox(
        min_lon=lon - lon_offset,
        min_lat=lat - lat_offset,
        max_lon=lon + lon_offset,
        max_lat=lat + lat_offset,
        limit=10,
        fields='id,thumb_256_url,geometry,computed_geometry,compass_angle,is_pano'
    )
    
    if not images or 'error' in images:
        return jsonify({'error': 'No imagery found'}), 404
    
    # Prefer panoramic images for better 3D experience
    images_sorted = sorted(images, key=lambda x: (not x.get('is_pano', False)))
    
    return jsonify({'data': images_sorted})


@play_bp.route('/mapillary-viewer')
def mapillary_viewer():
    """Embeddable Mapillary viewer for daily challenges with 1km default search radius"""
    lat = request.args.get('lat', 40.7128, type=float)
    lon = request.args.get('lon', -74.0060, type=float)
    radius = request.args.get('radius', 1000, type=int)
    
    from flask import current_app
    access_token = current_app.config.get('MAPILLARY_ACCESS_TOKEN', '')
    
    return render_template('play/mapillary_viewer.html',
                         lat=lat,
                         lon=lon,
                         radius=radius,
                         access_token=access_token)