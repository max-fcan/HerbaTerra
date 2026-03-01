from pathlib import Path

from flask import Blueprint, abort, current_app, send_from_directory

bp = Blueprint("geo", __name__, url_prefix="/geojson")


@bp.get("/<filename>")
def geojson_file(filename: str):
    """
    Fonction implementée par l'IA.
    Servir les fichiers GeoJSON de manière sécurisée en vérifiant que le fichier demandé est dans la liste des fichiers autorisés et existe dans le répertoire de données.
    Niveau de détail paramétrable via la configuration (config.py).
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
