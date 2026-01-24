# mapillary_client.py

import os
import time
import requests
from flask import current_app
from dotenv import load_dotenv
from typing import List, Dict, Any, Optional

load_dotenv()  # Load environment variables from .env file if present

# Fetch configuration from flask app config or directly from environment variables
if current_app:
    MAPILLARY_TOKEN = current_app.config.get("MAPILLARY_ACCESS_TOKEN")
else:
    # To remove for production code, only for standalone usage
    MAPILLARY_TOKEN = os.environ.get("MAPILLARY_ACCESS_TOKEN") or os.environ.get("MPY_ACCESS_TOKEN") or os.environ.get("MAPILLARY_TOKEN")


if not MAPILLARY_TOKEN:
    raise RuntimeError(
        "Please set MAPILLARY_ACCESS_TOKEN in config.py or your environment variables (or .env file)."
    )

GRAPH_MAPILLARY_URL = "https://graph.mapillary.com"
SESSION = requests.Session()
SESSION.headers.update({"Authorization": f"OAuth {MAPILLARY_TOKEN}"})


def _get(path: str, params: Optional[Dict[str, Any]] = None, retries: int = 3, timeout: float = 15) -> Dict[str, Any]:
    """Low-level GET wrapper to Mapillary's Graph API, with thorough error handling."""
    url = f"{GRAPH_MAPILLARY_URL}{path}"
    last_error: Optional[str] = None

    for attempt in range(1, retries + 1):
        try:
            resp = SESSION.get(url, params=params, timeout=timeout)
            resp.raise_for_status()
            return resp.json()
        except requests.Timeout as exc:
            last_error = f"timeout after {timeout} seconds"
            current_app.logger.warning(
                "Mapillary GET %s timed out (attempt %s/%s)", url, attempt, retries
            )
        except requests.HTTPError as exc:
            status = getattr(exc.response, "status_code", None)
            last_error = f"HTTP {status}: {exc}"

            # Do not retry on client errors except rate limiting (429).
            if status and status < 500 and status != 429:
                current_app.logger.error(
                    "Mapillary GET %s failed with status %s: %s", url, status, exc
                )
                return {"error": f"Mapillary API error {status}", "details": str(exc)}

            current_app.logger.warning(
                "Mapillary GET %s failed with status %s (attempt %s/%s)",
                url,
                status,
                attempt,
                retries,
            )
        except requests.RequestException as exc:
            last_error = str(exc)
            current_app.logger.warning(
                "Mapillary GET %s request error: %s (attempt %s/%s)",
                url,
                exc,
                attempt,
                retries,
            )

        if attempt < retries:
            backoff = min(2 ** (attempt - 1), 5)  # Exponential backoff capped at 5s
            time.sleep(backoff)

    current_app.logger.error(
        "Mapillary GET %s failed after %s attempts: %s", url, retries, last_error
    )
    return {"error": "Mapillary API request failed", "details": last_error}


def fetch_images_in_bbox(
    min_lon: float,
    min_lat: float,
    max_lon: float,
    max_lat: float,
    limit: int = 100,
    fields: str | list[str] = "id,captured_at,geometry",
) -> List[Dict[str, Any]]:
    """
    Fetch images inside a bounding box.

    `fields` can include nested fields such as:
      "id,captured_at,geometry,detections.id,detections.value"
    """
    if isinstance(fields, list):
        fields = ",".join(fields)
    params = {
        "bbox": f"{min_lon},{min_lat},{max_lon},{max_lat}",
        "limit": limit,
        "fields": fields,
    }
    data = _get("/images", params=params)
    return data.get("data", [])


def main():
    """Test fetching images from Mapillary."""
    # Simple smoke test
    min_lon, min_lat = 2.30, 48.85
    max_lon, max_lat = 2.32, 48.86

    print("Testing fetch_images_in_bbox...")
    images = fetch_images_in_bbox(
        min_lon=min_lon,
        min_lat=min_lat,
        max_lon=max_lon,
        max_lat=max_lat,
        limit=5,
        fields="id,captured_at,geometry,detections.id,detections.value",
    )
    if images:
        from pprint import pprint
        pprint(images)
    
    print("Got", len(images), "images")


if __name__ == "__main__":
    main()

