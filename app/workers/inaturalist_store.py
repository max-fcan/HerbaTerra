"""
Scraper orchestration for iNaturalist observations -> SQLite.
"""

from __future__ import annotations

import json
import time
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
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
from app.services.inaturalist_db import save_inat_response, init_db, get_db_connection

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
	commit_every_pages: int = 5,
	commit_every_observations: int | None = None,
	checkpoint_path: str | Path | None = None,
	resume_from_checkpoint: bool = True,
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
	max_retries: int = 3,
	backoff_factor: float = 0.5,
	retry_statuses: Sequence[int] | None = None,
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

	if commit_every_pages < 1:
		raise ValueError("commit_every_pages must be >= 1")
	if commit_every_observations is not None and commit_every_observations < 1:
		raise ValueError("commit_every_observations must be >= 1")

	client = session or requests.Session()
	current_page = start_page
	pages_fetched = 0
	observations_saved = 0
	last_page: int | None = None
	last_total_entries: int | None = None
	checkpoint_file = Path(checkpoint_path) if checkpoint_path else None

	if checkpoint_file and resume_from_checkpoint and checkpoint_file.exists():
		try:
			checkpoint = json.loads(checkpoint_file.read_text(encoding="utf-8"))
			checkpoint_page = checkpoint.get("next_page")
			checkpoint_updated_since = checkpoint.get("updated_since")
			if isinstance(checkpoint_page, int) and checkpoint_page >= 1:
				current_page = checkpoint_page
				LOGGER.info("Resuming from checkpoint page %s", current_page)
			if updated_since is None and isinstance(checkpoint_updated_since, str):
				updated_since = checkpoint_updated_since
		except (OSError, json.JSONDecodeError) as exc:
			LOGGER.warning("Failed to load checkpoint: %s", exc)

	LOGGER.info("Starting iNaturalist scrape into %s", db_path)

	init_db(db_path)
	with get_db_connection(db_path) as conn:
		pending_pages = 0
		pending_observations = 0

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
				max_retries=max_retries,
				backoff_factor=backoff_factor,
				retry_statuses=retry_statuses,
			)

			results = response.get("results", [])
			if not results:
				LOGGER.info("No results returned on page %s. Stopping.", current_page)
				break

			saved_count = save_inat_response(
				Path(db_path),
				{"results": results},
				connection=conn,
				commit=False,
				initialize=False,
			)
			pages_fetched += 1
			observations_saved += saved_count
			pending_pages += 1
			pending_observations += saved_count

			pagination = response.get("pagination") or {}
			last_total_entries = pagination.get("total_entries")
			last_page = pagination.get("page")

			LOGGER.info(
				"Page %s: saved %s observations (total saved: %s)",
				current_page,
				saved_count,
				observations_saved,
			)

			commit_due = pending_pages >= commit_every_pages
			if commit_every_observations is not None:
				commit_due = commit_due or pending_observations >= commit_every_observations
			if commit_due:
				conn.commit()
				pending_pages = 0
				pending_observations = 0
				if checkpoint_file:
					checkpoint_file.parent.mkdir(parents=True, exist_ok=True)
					checkpoint_payload = {
						"next_page": current_page + 1,
						"updated_since": updated_since,
						"pages_fetched": pages_fetched,
						"observations_saved": observations_saved,
						"timestamp": datetime.now(tz=timezone.utc).isoformat(),
					}
					checkpoint_file.write_text(
						json.dumps(checkpoint_payload, ensure_ascii=False, indent=2),
						encoding="utf-8",
					)

			if len(results) < per_page:
				break

			current_page += 1

			if delay_seconds > 0:
				time.sleep(delay_seconds)

		if pending_pages or pending_observations:
			conn.commit()
			if checkpoint_file:
				checkpoint_file.parent.mkdir(parents=True, exist_ok=True)
				checkpoint_payload = {
					"next_page": current_page,
					"updated_since": updated_since,
					"pages_fetched": pages_fetched,
					"observations_saved": observations_saved,
					"timestamp": datetime.now(tz=timezone.utc).isoformat(),
				}
				checkpoint_file.write_text(
					json.dumps(checkpoint_payload, ensure_ascii=False, indent=2),
					encoding="utf-8",
				)

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
        start_page=50,
        max_pages=75, # Fetched pages 0-50 already
        per_page=200,
        iconic_taxa=["Plantae"],
        order_by="date_added",
        order="asc",
        has=["geo", "photos"],
        quality_grade="research",
        # only keep observations with commercially-usable licenses
        license=["CC-BY", "CC-BY-ND", "CC-BY-SA", "CC0"],
        # request identifications to be included in response
        # extra=["identifications"],
		timeout=60.0,
    )
    from app.services.inaturalist_db import enrich_observations_with_location_tags
    enrich_observations_with_location_tags("temp/inat_test.db")