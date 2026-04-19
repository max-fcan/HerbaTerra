from __future__ import annotations

import time
from typing import Any

from flask import Blueprint, current_app, redirect, render_template, request, session, url_for

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


def _format_distance_km(distance_km: float | None) -> str:
    if distance_km is None:
        return "No guess submitted."
    if distance_km < 10:
        return f"{distance_km:.2f} km"
    if distance_km < 100:
        return f"{distance_km:.1f} km"
    return f"{round(distance_km):,} km"


def _format_timer(seconds: int) -> str:
    safe_seconds = max(0, int(seconds))
    minutes = safe_seconds // 60
    remaining_seconds = safe_seconds % 60
    return f"{minutes}m {remaining_seconds}s"


def _get_mapping(game_state: dict[str, Any], key: str) -> dict[str, Any]:
    value = game_state.get(key)
    if isinstance(value, dict):
        return value
    value = {}
    game_state[key] = value
    return value


def _get_round_scope(game_state: dict[str, Any], round_index: int) -> dict[str, Any]:
    round_plan = game_state.get("round_plan")
    if isinstance(round_plan, list) and 0 <= round_index < len(round_plan):
        candidate_scope = round_plan[round_index]
        if isinstance(candidate_scope, dict):
            return candidate_scope

    fallback_scope = game_state.get("scope")
    if isinstance(fallback_scope, dict):
        return fallback_scope
    return {}


@bp.get("", strict_slashes=False)
def play_home():
    if not is_replica_ready():
        return render_template("db_loading.html", replica_status=get_replica_status()), 503

    requested_scope = parse_play_scope(request.args)
    configured_rounds = max(1, int(current_app.config.get("PLAY_ROUNDS", 4)))
    timer_seconds = max(1, int(current_app.config.get("PLAY_GUESS_SECONDS", 30)))
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
        game_state: dict[str, Any] = {
            "scope": scope,
            "round_plan": round_plan,
            "round_images": {},
            "round_results": {},
            "round_started_at": {},
            "total_rounds": max(1, len(round_plan) or configured_rounds),
        }
        session[_PLAY_SESSION_KEY] = game_state
        session.modified = True
    else:
        game_state = existing_game
        existing_scope = game_state.get("scope")
        scope = _scope_signature(existing_scope if isinstance(existing_scope, dict) else requested_scope)
        round_plan = game_state.get("round_plan")
        if not isinstance(round_plan, list) or not round_plan:
            round_plan = build_round_plan(scope, configured_rounds, antarctica_probability)
        game_state["scope"] = scope
        game_state["round_plan"] = round_plan
        game_state["total_rounds"] = max(1, len(round_plan) or configured_rounds)
        _get_mapping(game_state, "round_images")
        _get_mapping(game_state, "round_results")
        _get_mapping(game_state, "round_started_at")
        session[_PLAY_SESSION_KEY] = game_state
        session.modified = True

    total_rounds = int(game_state.get("total_rounds") or configured_rounds)
    current_round_index = max(
        0,
        min((requested_step or 1) - 1, max(0, total_rounds - 1)),
    )
    current_round_plan = round_plan[current_round_index] if round_plan else None
    round_images = _get_mapping(game_state, "round_images")
    round_results = _get_mapping(game_state, "round_results")
    round_started_at = _get_mapping(game_state, "round_started_at")

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

    round_result_raw = round_results.get(round_key)
    round_result = round_result_raw if isinstance(round_result_raw, dict) else None
    round_started_timestamp: float | None = None

    if not play_error and round_result is None and round_key not in round_started_at:
        round_started_at[round_key] = time.time()
        session[_PLAY_SESSION_KEY] = game_state
        session.modified = True

    started_at_raw = round_started_at.get(round_key)
    try:
        round_started_timestamp = float(started_at_raw)
    except (TypeError, ValueError):
        round_started_timestamp = None

    seconds_remaining = timer_seconds
    if round_result is None and round_started_timestamp is not None:
        seconds_remaining = max(
            0,
            int(round_started_timestamp + timer_seconds - time.time()),
        )

    if round_result:
        round_result = {
            **round_result,
            "distance_text": _format_distance_km(
                float(round_result["distance_km"])
                if round_result.get("distance_km") is not None
                else None
            ),
        }

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
        seconds_remaining=seconds_remaining,
        timer_display=_format_timer(seconds_remaining),
        round=current_round,
        round_result=round_result,
        current_step=current_round_index + 1,
        geojson_url=url_for("geo.geojson_file", filename=selected_geojson_file),
        submit_guess_url=url_for("play.submit_round"),
        has_next_round=has_next_round,
        next_round_url=next_round_url,
        restart_url=restart_url,
        continent_names_by_iso_code=continent_names_by_iso_code,
    )


@bp.post("/submit")
def submit_round():
    if not is_replica_ready():
        return render_template("db_loading.html", replica_status=get_replica_status()), 503

    game_state = session.get(_PLAY_SESSION_KEY)
    if not isinstance(game_state, dict):
        return redirect(url_for("pages.hub"))

    round_index = request.form.get("round_index", default=0, type=int)
    total_rounds = max(1, int(game_state.get("total_rounds") or 1))
    round_index = max(0, min(round_index, total_rounds - 1))
    round_key = str(round_index)

    round_images = _get_mapping(game_state, "round_images")
    round_results = _get_mapping(game_state, "round_results")
    round_started_at = _get_mapping(game_state, "round_started_at")

    if isinstance(round_results.get(round_key), dict):
        return redirect(url_for("play.play_home", step=round_index + 1))

    round_data = round_images.get(round_key)
    if not isinstance(round_data, dict):
        return redirect(url_for("play.play_home", step=round_index + 1))

    started_at_raw = round_started_at.get(round_key)
    try:
        started_at = float(started_at_raw)
    except (TypeError, ValueError):
        started_at = time.time()
        round_started_at[round_key] = started_at

    timer_seconds = max(1, int(current_app.config.get("PLAY_GUESS_SECONDS", 30)))

    guess_latitude: float | None = None
    guess_longitude: float | None = None

    guess_latitude_raw = request.form.get("guess_latitude")
    guess_longitude_raw = request.form.get("guess_longitude")
    if guess_latitude_raw and guess_longitude_raw:
        try:
            parsed_latitude = float(guess_latitude_raw)
            parsed_longitude = float(guess_longitude_raw)
        except (TypeError, ValueError):
            parsed_latitude = None
            parsed_longitude = None
        if (
            parsed_latitude is not None
            and parsed_longitude is not None
            and -90.0 <= parsed_latitude <= 90.0
            and -180.0 <= parsed_longitude <= 180.0
        ):
            guess_latitude = parsed_latitude
            guess_longitude = parsed_longitude

    round_scope = _get_round_scope(game_state, round_index)
    solution_latitude = float(round_data.get("latitude") or 0.0)
    solution_longitude = float(round_data.get("longitude") or 0.0)

    distance_km: float | None = None
    if guess_latitude is not None and guess_longitude is not None:
        distance_km = haversine_distance_km(
            guess_latitude,
            guess_longitude,
            solution_latitude,
            solution_longitude,
        )

    submitted_at = time.time()
    timed_out = submitted_at > started_at + timer_seconds
    scale_meters = get_scope_scale_meters(round_scope)
    score = (
        compute_geoguessr_score(distance_km, scale_meters)
        if distance_km is not None and not timed_out
        else 0
    )

    current_app.logger.debug(
        "Play round submitted: round_index=%s timed_out=%s guess=(%r,%r) solution=(%.6f,%.6f) score=%s",
        round_index,
        timed_out,
        guess_latitude,
        guess_longitude,
        solution_latitude,
        solution_longitude,
        score,
    )

    round_results[round_key] = {
        "guess_latitude": guess_latitude,
        "guess_longitude": guess_longitude,
        "distance_km": distance_km,
        "score": score,
        "timed_out": timed_out,
        "submitted_at": submitted_at,
        "time_limit_seconds": timer_seconds,
    }
    session[_PLAY_SESSION_KEY] = game_state
    session.modified = True

    return redirect(url_for("play.play_home", step=round_index + 1))
