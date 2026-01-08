import requests
from pprint import pprint

INAT_API = "https://api.inaturalist.org/v1/observations"

def fetch_plant_observations(
    per_page: int = 30,
    page: int = 1
) -> list[dict]:
    params = {
        "taxon_id": 47126,          # Plantae
        "photos": "true",           # must have photos
        "geo": "true",              # must have coordinates
        "quality_grade": "research,needs_id",
        "per_page": per_page,
        "page": page,
        "order_by": "random"
    }

    response = requests.get(INAT_API, params=params, timeout=10)
    response.raise_for_status()
    return response.json()["results"]


def extract_useful_data(observation: dict) -> dict | None:
    photos = observation.get("photos", [])
    if not photos:
        return None

    photo = photos[0]

    return {
        "observation_id": observation["id"],
        "lat": observation["geojson"]["coordinates"][1],
        "lon": observation["geojson"]["coordinates"][0],
        "scientific_name": observation["taxon"]["name"]
            if observation.get("taxon") else None,
        "image_url": photo["url"].replace("square", "large")
    }

if __name__ == "__main__":
    observations = fetch_plant_observations(per_page=5)
    for obs in observations:
        data = extract_useful_data(obs)
        if data:
            pprint(data)