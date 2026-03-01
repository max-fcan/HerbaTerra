from flask import Blueprint, render_template

bp = Blueprint("quiz", __name__, url_prefix="/quiz")


@bp.get("", strict_slashes=False)
@bp.get("/")
def index():
    return render_template("quiz/index.html", completion_rate=25)
