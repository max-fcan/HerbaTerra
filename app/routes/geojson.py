from pathlib import Path

from flask import Blueprint, abort, current_app, send_from_directory

bp = Blueprint("geo", __name__, url_prefix="/geojson")


@bp.get("/<filename>")
def geojson_file(filename: str):
    """
    AI-implemented helper.
    Serve GeoJSON files safely by checking that the requested file is allowed and exists in the data directory.
    The detail level is configurable via config.py.
    """
    allowed_files = set(current_app.config["_MAP_GEOJSON_FILES"].values())
    if filename not in allowed_files or not (
        Path(current_app.config["DATA_DIR"]) / filename
    ).exists():
        abort(404)
    return send_from_directory(
        current_app.config["DATA_DIR"],
        filename,
        mimetype="application/geo+json",
    )
