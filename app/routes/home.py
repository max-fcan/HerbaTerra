from flask import Blueprint, render_template

bp = Blueprint("home", __name__, url_prefix="/home")


@bp.get("", strict_slashes=False)
@bp.get("/")
def home():
    return render_template("home/index.html")
