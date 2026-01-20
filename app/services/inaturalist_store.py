"""
Scraper orchestration for iNaturalist observations -> SQLite.
"""

from __future__ import annotations

import time
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

import requests

from app.logging_config import configure_logging
from app.services.inaturalist_api import (
	get_observation,
	ObservationResponse,
	Order,
	OrderBy,
	License,
	Licenses,
	IconicTaxonName,
	HasFilter,
	QualityGrade,
	Extra,
)
from app.services.inaturalist_db import save_inat_response

LOGGER = configure_logging(
	level=logging.INFO,
	logger_name=__name__,
	log_filename="inaturalist_store.log",
)


@dataclass(frozen=True)
class ScrapeSummary:
	pages_fetched: int
	observations_saved: int
	total_entries: int | None
	last_page: int | None


def scrape_observations_to_sqlite(
	*,
	db_path: str | Path,
	max_pages: int | None = None,
	start_page: int = 1,
	per_page: int = 200,
	delay_seconds: float = 0.5,
	q: str | None = None,
	order_by: OrderBy | None = None,
	order: Order | None = None,
	license: Licenses | License | None = None,
	photo_license: Licenses | License | None = None,
	taxon_id: int | None = None,
	taxon_name: str | None = None,
	iconic_taxa: Sequence[IconicTaxonName] | None = None,
	has: Sequence[HasFilter] | None = None,
	quality_grade: QualityGrade | None = None,
	out_of_range: bool | None = None,
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
	extra: Sequence[Extra] | None = ["identifications"],
	session: requests.Session | None = None,
	timeout: float = 15.0,
) -> ScrapeSummary:
	"""
	Scrape observations and store them into SQLite.
	"""
	if start_page < 1:
		raise ValueError("start_page must be >= 1")
	if max_pages is not None and max_pages < 1:
		raise ValueError("max_pages must be >= 1")
	if delay_seconds < 0:
		raise ValueError("delay_seconds must be >= 0")

	client = session or requests.Session()
	current_page = start_page
	pages_fetched = 0
	observations_saved = 0
	last_page: int | None = None
	last_total_entries: int | None = None

	LOGGER.info("Starting iNaturalist scrape into %s", db_path)

	while True:
		if max_pages is not None and pages_fetched >= max_pages:
			break

		response: ObservationResponse = get_observation(
			q=q,
			page=current_page,
			per_page=per_page,
			order_by=order_by,
			order=order,
			license=license,
			photo_license=photo_license,
			taxon_id=taxon_id,
			taxon_name=taxon_name,
			iconic_taxa=iconic_taxa,
			has=has,
			quality_grade=quality_grade,
			out_of_range=True if out_of_range else None,
			on=on,
			year=year,
			month=month,
			day=day,
			d1=d1,
			d2=d2,
			m1=m1,
			m2=m2,
			h1=h1,
			h2=h2,
			swlat=swlat,
			swlng=swlng,
			nelat=nelat,
			nelng=nelng,
			list_id=list_id,
			updated_since=updated_since,
			extra=extra,
			session=client,
			timeout=timeout,
		)

		results = response.get("results", [])
		if not results:
			LOGGER.info("No results returned on page %s. Stopping.", current_page)
			break

		saved_count = save_inat_response(Path(db_path), {"results": results})
		pages_fetched += 1
		observations_saved += saved_count

		pagination = response.get("pagination") or {}
		last_total_entries = pagination.get("total_entries")
		last_page = pagination.get("page")

		LOGGER.info(
			"Page %s: saved %s observations (total saved: %s)",
			current_page,
			saved_count,
			observations_saved,
		)

		if len(results) < per_page:
			break

		current_page += 1

		if delay_seconds > 0:
			time.sleep(delay_seconds)

	return ScrapeSummary(
		pages_fetched=pages_fetched,
		observations_saved=observations_saved,
		total_entries=last_total_entries,
		last_page=last_page,
	)


__all__ = ["ScrapeSummary", "scrape_observations_to_sqlite"]


if __name__ == "__main__":
    resp = scrape_observations_to_sqlite(
        db_path="temp/inat_test.db",
        max_pages=10,
        per_page=200,
        iconic_taxa=["Plantae"],
        order_by="date_added",
        order="asc",
        has=["geo", "photos"],
        quality_grade="research",
        # only keep observations with commercially-usable licenses
        license=["CC-BY", "CC-BY-ND", "CC-BY-SA", "CC0"],
        # request identifications to be included in response
        extra=["identifications"],
		timeout=60.0,
    )