from __future__ import annotations

from math import isfinite

from flask import Blueprint, current_app, jsonify, render_template, request, session, url_for

from app.db.connections import get_replica_status, is_replica_ready
from app.services.geocoding import get_continent_names_by_iso
from app.services.play import (
    build_round_plan,
    compute_geoguessr_score,
    get_scope_label,
    get_scope_scale_meters,
    haversine_distance_km,
    parse_play_scope,
    select_random_round_image,
)

bp = Blueprint("play", __name__, url_prefix="/play")
_PLAY_SESSION_KEY = "play_game_v1"


def _scope_signature(scope: dict[str, str]) -> dict[str, str]:
    return {
        "scope_type": scope.get("scope_type", "world"),
        "country_code": scope.get("country_code", ""),
        "country": scope.get("country", ""),
        "continent_code": scope.get("continent_code", ""),
        "continent": scope.get("continent", ""),
    }


def _has_scope_args() -> bool:
    return any(
        bool(str(request.args.get(key, "")).strip())
        for key in ("country_code", "continent_code")
    )


def _scope_display(scope: dict[str, str]) -> str:
    scope_type = scope.get("scope_type")
    if scope_type == "country":
        return (scope.get("country") or scope.get("country_code") or "World").upper().split(",")[0]
    if scope_type == "continent":
        return (scope.get("continent") or scope.get("continent_code") or "World").upper()
    return "WORLD"


@bp.get("", strict_slashes=False)
def play_home():
    if not is_replica_ready():
        return render_template("db_loading.html", replica_status=get_replica_status()), 503

    requested_scope = parse_play_scope(request.args)
    configured_rounds = max(1, int(current_app.config.get("PLAY_ROUNDS", 4)))
    timer_seconds = max(1, int(current_app.config.get("PLAY_GUESS_SECONDS", 30)))
    reveal_after_submit = bool(current_app.config.get("PLAY_REVEAL_AFTER_SUBMIT", True))
    antarctica_probability = float(
        current_app.config.get("PLAY_WORLD_ANTARCTICA_PROBABILITY", 0.05)
    )
    requested_step = request.args.get("step", default=None, type=int)
    is_step_navigation = requested_step is not None
    force_new_game = (
        request.args.get("new", default="", type=str).strip().lower()
        in {"1", "true", "yes"}
    )
    if _has_scope_args():
        force_new_game = True
    if not is_step_navigation:
        force_new_game = True

    existing_game = session.get(_PLAY_SESSION_KEY)
    if not isinstance(existing_game, dict):
        existing_game = None

    if force_new_game or existing_game is None:
        scope = _scope_signature(requested_scope)
        round_plan = build_round_plan(scope, configured_rounds, antarctica_probability)
        game_state: dict[str, object] = {
            "scope": scope,
            "round_plan": round_plan,
            "round_images": {},
            "total_rounds": max(1, len(round_plan) or configured_rounds),
        }
        session[_PLAY_SESSION_KEY] = game_state
        session.modified = True
    else:
        game_state = existing_game
        existing_scope = game_state.get("scope")
        scope = _scope_signature(existing_scope if isinstance(existing_scope, dict) else requested_scope)
        round_plan = game_state.get("round_plan")
        if not isinstance(round_plan, list):
            round_plan = build_round_plan(scope, configured_rounds, antarctica_probability)
        if not round_plan:
            round_plan = build_round_plan(scope, configured_rounds, antarctica_probability)
        game_state["scope"] = scope
        game_state["round_plan"] = round_plan
        game_state.setdefault("round_images", {})
        game_state["total_rounds"] = max(1, len(round_plan) or configured_rounds)
        session[_PLAY_SESSION_KEY] = game_state
        session.modified = True

    total_rounds = int(game_state.get("total_rounds") or configured_rounds) # pyright: ignore[reportArgumentType]
    current_round_index = max(
        0,
        min((requested_step or 1) - 1, max(0, total_rounds - 1)),
    )
    current_round_plan = round_plan[current_round_index] if round_plan else None
    round_images = game_state.get("round_images")
    if not isinstance(round_images, dict):
        round_images = {}
        game_state["round_images"] = round_images

    round_key = str(current_round_index)
    current_round = round_images.get(round_key)
    if current_round is None and current_round_plan is not None:
        current_round = select_random_round_image(current_round_plan)
        if current_round is not None:
            round_images[round_key] = current_round
            session[_PLAY_SESSION_KEY] = game_state
            session.modified = True

    play_error = None
    if not current_round:
        play_error = (
            "No eligible plant image was found for this scope. "
            "Try a different area from the hub map."
        )

    has_next_round = current_round_index + 1 < total_rounds
    next_round_url = (
        url_for("play.play_home", step=current_round_index + 2)
        if has_next_round
        else ""
    )
    restart_url = url_for("pages.hub")

    selected_geojson_file = current_app.config["MAP_GEOJSON_FILE"]
    try:
        continent_names_by_iso_code = get_continent_names_by_iso()
    except FileNotFoundError:
        current_app.logger.warning(
            "ISO3166 CSV not found; continent labels disabled in play map popups."
        )
        continent_names_by_iso_code = {}

    return render_template(
        "play.html",
        play_error=play_error,
        scope=scope,
        scope_display=_scope_display(scope),
        scope_label=get_scope_label(scope),
        total_rounds=total_rounds,
        current_round_index=current_round_index,
        timer_seconds=timer_seconds,
        reveal_after_submit=reveal_after_submit,
        round_plan=round_plan,
        round=current_round,
        geojson_url=url_for("geo.geojson_file", filename=selected_geojson_file),
        submit_guess_url=url_for("play.submit_guess"),
        score_guess_url=url_for("play.score_guess"),
        has_next_round=has_next_round,
        next_round_url=next_round_url,
        restart_url=restart_url,
        continent_names_by_iso_code=continent_names_by_iso_code,
    )


@bp.post("/guess")
def submit_guess():
    if not is_replica_ready():
        return jsonify(get_replica_status()), 503

    payload = request.get_json(silent=True) or {}
    latitude_raw = payload.get("latitude")
    longitude_raw = payload.get("longitude")
    round_index = payload.get("round_index")

    try:
        latitude = float(latitude_raw) # pyright: ignore[reportArgumentType]
        longitude = float(longitude_raw) # pyright: ignore[reportArgumentType]
    except (TypeError, ValueError):
        return jsonify({"ok": False, "error": "Invalid coordinates"}), 400

    if not (
        isfinite(latitude)
        and isfinite(longitude)
        and -90.0 <= latitude <= 90.0
        and -180.0 <= longitude <= 180.0
    ):
        return jsonify({"ok": False, "error": "Coordinates out of range"}), 400

    current_app.logger.info(
        "Play guess submitted: latitude_raw=%r longitude_raw=%r latitude=%.12f longitude=%.12f round_index=%r",
        latitude_raw,
        longitude_raw,
        latitude,
        longitude,
        round_index,
    )

    return jsonify(
        {
            "ok": True,
            "reveal_after_submit": bool(
                current_app.config.get("PLAY_REVEAL_AFTER_SUBMIT", True)
            ),
        }
    )


@bp.post("/score")
def score_guess():
    if not is_replica_ready():
        return jsonify(get_replica_status()), 503

    payload = request.get_json(silent=True) or {}
    round_index_raw = payload.get("round_index")
    guess_latitude = payload.get("guess_latitude")
    guess_longitude = payload.get("guess_longitude")
    solution_latitude_raw = payload.get("solution_latitude")
    solution_longitude_raw = payload.get("solution_longitude")

    try:
        round_index = int(round_index_raw)
    except (TypeError, ValueError):
        return jsonify({"ok": False, "error": "Invalid round index"}), 400

    game_state = session.get(_PLAY_SESSION_KEY)
    if not isinstance(game_state, dict):
        return jsonify({"ok": False, "error": "No active game"}), 400

    round_images = game_state.get("round_images")
    if not isinstance(round_images, dict):
        return jsonify({"ok": False, "error": "No active round data"}), 400

    round_data = round_images.get(str(round_index))
    if not isinstance(round_data, dict):
        return jsonify({"ok": False, "error": "Round image not found"}), 404

    round_plan = game_state.get("round_plan")
    round_scope: dict[str, Any] = {}
    if isinstance(round_plan, list) and 0 <= round_index < len(round_plan):
        candidate_scope = round_plan[round_index]
        if isinstance(candidate_scope, dict):
            round_scope = candidate_scope
    if not round_scope:
        fallback_scope = game_state.get("scope")
        if isinstance(fallback_scope, dict):
            round_scope = fallback_scope

    solution_latitude = float(round_data.get("latitude") or 0.0)
    solution_longitude = float(round_data.get("longitude") or 0.0)

    has_guess = guess_latitude is not None and guess_longitude is not None
    parsed_guess_latitude: float | None = None
    parsed_guess_longitude: float | None = None
    if has_guess:
        try:
            parsed_guess_latitude = float(guess_latitude) # pyright: ignore[reportArgumentType]
            parsed_guess_longitude = float(guess_longitude) # pyright: ignore[reportArgumentType]
        except (TypeError, ValueError):
            return jsonify({"ok": False, "error": "Invalid guess coordinates"}), 400

        if not (
            isfinite(parsed_guess_latitude)
            and isfinite(parsed_guess_longitude)
            and -90.0 <= parsed_guess_latitude <= 90.0
            and -180.0 <= parsed_guess_longitude <= 180.0
        ):
            return jsonify({"ok": False, "error": "Guess coordinates out of range"}), 400

    scale_meters = get_scope_scale_meters(round_scope)
    distance_km: float
    if parsed_guess_latitude is None or parsed_guess_longitude is None:
        distance_km = 20_037.5
        score = 0
    else:
        distance_km = haversine_distance_km(
            parsed_guess_latitude,
            parsed_guess_longitude,
            solution_latitude,
            solution_longitude,
        )
        score = compute_geoguessr_score(distance_km, scale_meters)

    current_app.logger.info(
        "Play score requested: round_index=%r guess=(%r,%r) payload_solution=(%r,%r) actual_solution=(%.6f,%.6f) distance_km=%.3f scale_m=%.1f score=%s",
        round_index,
        guess_latitude,
        guess_longitude,
        solution_latitude_raw,
        solution_longitude_raw,
        solution_latitude,
        solution_longitude,
        distance_km,
        scale_meters,
        score,
    )

    return jsonify(
        {
            "ok": True,
            "status": "ready",
            "score": score,
            "distance_km": distance_km,
            "scale_meters": scale_meters,
        }
    )
