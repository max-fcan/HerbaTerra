"""Landing pages — ``/`` and ``/about``."""

from flask import Blueprint, render_template

landing_bp = Blueprint("landing", __name__)


@landing_bp.route("/")
def index():
    """Landing page with 3-D Earth background."""
    return render_template("landing/index.html", background_quality="medium")


@landing_bp.route("/about")
def about():
    """About page."""
    return render_template("landing/about.html")
