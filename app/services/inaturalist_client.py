import requests
from typing import Any, Dict, List, Literal
from pprint import pprint

LICENSES = "CC0,CC-BY,CC-BY-SA,CC-BY-ND"  # List formatted for iNaturalist API requests

INAT_API = "https://api.inaturalist.org/v1/observations"


def _extract_useful_data(observation: dict) -> dict | None:
    photos = observation.get("photos", [])
    if not photos:
        return None

    photo = photos[0]

    return {
        "observation_id": observation.get("id"),
        "lat": observation.get("geojson", {}).get("coordinates", [None, None])[1],
        "lon": observation.get("geojson", {}).get("coordinates", [None, None])[0],
        "scientific_name": observation.get("taxon", {}).get("name"),
        "image_url": photo.get("url", "").replace("square", "large")
    }


def fetch_plant_observations(
    per_page: int,
    page: int = 1,
    order_by: Literal["created_at", "geo_score", "id", "observed_on", "random", "species_guess", "updated_at", "vptes"] = "random"
) -> list[dict]:
    params = {
        "taxon_id": 47126,          # Plantae
        "photos": "true",           # must have photos
        "geo": "true",              # must have coordinates
        "quality_grade": "research,needs_id",
        "per_page": per_page,
        "page": page,
        "licenses": LICENSES,
        "order_by": order_by
    }

    response = requests.get(INAT_API, params=params, timeout=10)
    response.raise_for_status()
    return [_extract_useful_data(obs) for obs in response.json()["results"]]


if __name__ == "__main__":
    observations = fetch_plant_observations(
        per_page=5,
        page=1,
        order_by="random"
    )
    for obs in observations:
        if obs:
            pprint(obs)