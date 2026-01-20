"""
iNaturalist API client (typed).

Implements a strictly-typed helper for GET /observations.
"""

from __future__ import annotations

from typing import TypedDict, Literal, NotRequired, Sequence, cast

import time

import requests

INAT_API_BASE_URL = "https://inaturalist.org/"

OrderBy = Literal["observed_on", "date_added"]
Order = Literal["asc", "desc"]
License = Literal[
	"none",
	"any",
	"CC-BY",
	"CC-BY-NC",
	"CC-BY-SA",
	"CC-BY-ND",
	"CC-BY-NC-SA",
	"CC-BY-NC-ND",
	"CC0",
]
Licenses = list[License]
IconicTaxonName = Literal[
	"Plantae",
	"Animalia",
	"Mollusca",
	"Reptilia",
	"Aves",
	"Amphibia",
	"Actinopterygii",
	"Mammalia",
	"Insecta",
	"Arachnida",
	"Fungi",
	"Protozoa",
	"Chromista",
	"unknown",
]
HasFilter = Literal["photos", "geo"]
QualityGrade = Literal["casual", "research"]
Extra = Literal["fields", "identifications", "projects"]


class PaginationHeaders(TypedDict):
	total_entries: int | None
	page: int | None
	per_page: int | None


class IconicTaxon(TypedDict):
	id: int
	name: IconicTaxonName
	rank: str
	ancestry: NotRequired[str]


class Taxon(TypedDict):
	id: int
	name: str
	rank: NotRequired[str]
	iconic_taxon_name: NotRequired[IconicTaxonName]


class User(TypedDict):
	id: int
	login: str


class GeoJSON(TypedDict):
	type: str
	coordinates: list[float]


class Photo(TypedDict):
	id: int
	url: str
	license_code: NotRequired[str | None]


class Observation(TypedDict):
	id: int
	observed_on: str | None
	created_at: str | None
	updated_at: str | None
	quality_grade: QualityGrade | None
	latitude: float | None
	longitude: float | None
	positional_accuracy: float | None
	taxon_id: int | None
	user_login: str | None
	place_guess: str | None
	species_guess: str | None
	license: Licenses | License | None
	geoprivacy: str | None
	coordinates_obscured: bool | None
	iconic_taxon: NotRequired[IconicTaxon]
	taxon: NotRequired[Taxon]
	user: NotRequired[User]
	photos: NotRequired[list[Photo]]
	geojson: NotRequired[GeoJSON]


class ObservationResponse(TypedDict):
	results: list[Observation]
	pagination: PaginationHeaders


def _parse_int(value: str | None) -> int | None:
	if value is None:
		return None
	value = value.strip()
	if not value:
		return None
	try:
		return int(value)
	except ValueError:
		return None


def _validate_range(name: str, value: int | float, min_value: int | float, max_value: int | float) -> None:
	if value < min_value or value > max_value:
		raise ValueError(f"{name} must be between {min_value} and {max_value}")


def get_observation(
	*,
	q: str | None = None,
	page: int | None = None,
	per_page: int | None = None,
	order_by: OrderBy | None = None,
	order: Order | None = None,
	license: Licenses | License | None = None,
	photo_license: Licenses | License | None = None,
	taxon_id: int | None = None,
	taxon_name: str | None = None,
	iconic_taxa: Sequence[IconicTaxonName] | None = None,
	has: Sequence[HasFilter] | None = None,
	quality_grade: QualityGrade | None = None,
	out_of_range: Literal[True] | None = None,
	on: str | None = None,
	year: int | None = None,
	month: int | None = None,
	day: int | None = None,
	d1: str | None = None,
	d2: str | None = None,
	m1: int | None = None,
	m2: int | None = None,
	h1: int | None = None,
	h2: int | None = None,
	swlat: float | None = None,
	swlng: float | None = None,
	nelat: float | None = None,
	nelng: float | None = None,
	list_id: int | None = None,
	updated_since: str | None = None,
	extra: Sequence[Extra] | None = None,
	timeout: float = 15.0,
	session: requests.Session | None = None,
	max_retries: int = 3,
	backoff_factor: float = 0.5,
	retry_statuses: Sequence[int] | None = None,
) -> ObservationResponse:
	"""
	Retrieve observations from iNaturalist.

	This wraps GET /observations and returns a normalized response with
	results and pagination headers (when present).
	"""
	if per_page is not None:
		_validate_range("per_page", per_page, 1, 200)
	if month is not None:
		_validate_range("month", month, 1, 12)
	if day is not None:
		_validate_range("day", day, 1, 31)
	if m1 is not None:
		_validate_range("m1", m1, 1, 12)
	if m2 is not None:
		_validate_range("m2", m2, 1, 12)
	if h1 is not None:
		_validate_range("h1", h1, 0, 23)
	if h2 is not None:
		_validate_range("h2", h2, 0, 23)
	if swlat is not None:
		_validate_range("swlat", swlat, -90, 90)
	if nelat is not None:
		_validate_range("nelat", nelat, -90, 90)
	if swlng is not None:
		_validate_range("swlng", swlng, -180, 180)
	if nelng is not None:
		_validate_range("nelng", nelng, -180, 180)

	params: dict[str, str | int | float | Sequence[str] | Sequence[IconicTaxonName] | Sequence[HasFilter] | Sequence[Extra]] = {}

	if q is not None:
		params["q"] = q
	if page is not None:
		params["page"] = page
	if per_page is not None:
		params["per_page"] = per_page
	if order_by is not None:
		params["order_by"] = order_by
	if order is not None:
		params["order"] = order
	if license is not None:
		if isinstance(license, list):
			params["license"] = ",".join(license)
		else:
			params["license"] = license
	if photo_license is not None:
		params["photo_license"] = photo_license
	if taxon_id is not None:
		params["taxon_id"] = taxon_id
	if taxon_name is not None:
		params["taxon_name"] = taxon_name
	if iconic_taxa is not None:
		params["iconic_taxa[]"] = iconic_taxa
	if has is not None:
		params["has[]"] = has
	if quality_grade is not None:
		params["quality_grade"] = quality_grade
	if out_of_range is not None:
		params["out_of_range"] = "true"
	if on is not None:
		params["on"] = on
	if year is not None:
		params["year"] = year
	if month is not None:
		params["month"] = month
	if day is not None:
		params["day"] = day
	if d1 is not None:
		params["d1"] = d1
	if d2 is not None:
		params["d2"] = d2
	if m1 is not None:
		params["m1"] = m1
	if m2 is not None:
		params["m2"] = m2
	if h1 is not None:
		params["h1"] = h1
	if h2 is not None:
		params["h2"] = h2
	if swlat is not None:
		params["swlat"] = swlat
	if swlng is not None:
		params["swlng"] = swlng
	if nelat is not None:
		params["nelat"] = nelat
	if nelng is not None:
		params["nelng"] = nelng
	if list_id is not None:
		params["list_id"] = list_id
	if updated_since is not None:
		params["updated_since"] = updated_since
	if extra is not None:
		params["extra"] = extra

	client = session or requests.Session()
	statuses = set(retry_statuses or [429, 500, 502, 503, 504])

	attempt = 0
	while True:
		try:
			response = client.get(
				f"{INAT_API_BASE_URL}/observations.json",
				params=params,
				timeout=timeout,
			)
			if response.status_code in statuses:
				raise requests.HTTPError(f"Retryable HTTP status: {response.status_code}", response=response)
			response.raise_for_status()
			break
		except requests.RequestException:
			if attempt >= max_retries:
				raise
			sleep_seconds = backoff_factor * (2**attempt)
			if "response" in locals() and response is not None:
				retry_after = response.headers.get("Retry-After")
				if retry_after:
					try:
						sleep_seconds = max(sleep_seconds, float(retry_after))
					except ValueError:
						pass
			time.sleep(sleep_seconds)
			attempt += 1

	data = response.json()
	results: list[Observation]

	if isinstance(data, dict) and isinstance(data.get("results"), list):
		results = cast(list[Observation], data["results"])
	elif isinstance(data, list):
		results = cast(list[Observation], data)
	else:
		raise ValueError("Unexpected iNaturalist response format")

	pagination: PaginationHeaders = {
		"total_entries": _parse_int(response.headers.get("X-Total-Entries")),
		"page": _parse_int(response.headers.get("X-Page")),
		"per_page": _parse_int(response.headers.get("X-Per-Page")),
	}

	return {
		"results": results,
		"pagination": pagination,
	}

if __name__ == "__main__":
    resp = get_observation(
        per_page=5,
        iconic_taxa=["Plantae"],
    )
    
    from pprint import pprint
    pprint(resp)
