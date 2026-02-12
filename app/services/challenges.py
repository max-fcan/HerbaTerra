import duckdb
from random import randint
from threading import Lock

_CONNECTION = duckdb.connect("data/gbif_plants.duckdb", read_only=True)
_QUERY_LOCK = Lock()


class Challenge:
    def __init__(
        self,
        continent: str | None = None,
        country: str | None = None,
        admin1: str | None = None,
        admin2: str | None = None,
        city: str | None = None,
    ):
        result = self.get_plant_sample(continent, country, admin1, admin2, city)
        if result is None:
            self.url = None
            self.solution = None
            self.proposed_locations = None
            return

        self.url, self.solution = result
        self.proposed_locations = self.get_proposed_locations(self.solution)

    def to_dict(self) -> dict:
        return {
            "url": self.url,
            "solution": self.solution,
            "proposed_locations": self.proposed_locations,
        }

    def _fetchone(self, query: str, params: list | None = None):
        with _QUERY_LOCK:
            return _CONNECTION.execute(query, params or []).fetchone()

    def _fetchall(self, query: str, params: list | None = None):
        with _QUERY_LOCK:
            return _CONNECTION.execute(query, params or []).fetchall()

    def _build_filter_clause(
        self,
        continent: str | None = None,
        country: str | None = None,
        admin1: str | None = None,
        admin2: str | None = None,
        city: str | None = None,
    ) -> tuple[str, list]:
        conditions: list[str] = []
        params: list[str] = []

        if continent:
            conditions.append("continent = ?")
            params.append(continent.upper())
        if country:
            conditions.append("country = ?")
            params.append(country)
        if admin1:
            conditions.append("admin1 = ?")
            params.append(admin1)
        if admin2:
            conditions.append("admin2 = ?")
            params.append(admin2)
        if city:
            conditions.append("city = ?")
            params.append(city)

        where_clause = " AND ".join(conditions) if conditions else "TRUE"
        return where_clause, params

    def get_plant_sample(
        self,
        continent: str | None = None,
        country: str | None = None,
        admin1: str | None = None,
        admin2: str | None = None,
        city: str | None = None,
    ) -> tuple | None:
        where_clause, params = self._build_filter_clause(continent, country, admin1, admin2, city)

        total_rows_query = f"SELECT COUNT(*) FROM images WHERE {where_clause};"
        if _result:=self._fetchone(total_rows_query, params):
            total_rows = _result[0]
        else:
            total_rows = 0
        if total_rows == 0:
            return None

        random_offset = randint(0, total_rows - 1)
        sample_query = f"""
        SELECT image_url, lat, lon, continent, country, admin1, admin2, city
        FROM images
        WHERE {where_clause}
        LIMIT 1 OFFSET ?;
        """
        row = self._fetchone(sample_query, [*params, random_offset])
        if not row:
            return None

        return (
            row[0],
            {
                "coordinates": {"lat": row[1], "lon": row[2]},
                "location": self._format_location(*row[3:8]),
                "continent": row[3],
                "details": self._format_location(*row[4:8]),
            },
        )

    def _format_location(self, *tags) -> str:
        def _camel_case(s: str) -> str:
            return " ".join(word.capitalize() for word in s.split(" "))

        length = len(tags)

        parts = [
            tags[0] if length > 0 else "",  # continent
            tags[1] if length > 1 else "",  # country
            tags[2] if length > 2 else "",  # admin1
            tags[3] if length > 3 else "",  # admin2
            tags[4] if length > 4 else "",  # city
        ]
        return ", ".join([_camel_case(part) for part in parts if part])

    def get_proposed_locations(self, solution: dict) -> list[dict]:
        base_query = """
        SELECT DISTINCT lat, lon, continent, country, admin1, admin2, city
        FROM images
        WHERE continent IS NOT NULL
          AND country IS NOT NULL
          AND lat IS NOT NULL
          AND lon IS NOT NULL
          AND NOT (lat = ? AND lon = ?)
        """
        base_params = [solution["coordinates"]["lat"], solution["coordinates"]["lon"]]

        total_rows_query = f"SELECT COUNT(*) FROM ({base_query}) AS candidates;"
        if _result:=self._fetchone(total_rows_query, base_params):
            total_rows = _result[0]
        else:
            total_rows = 0
        if total_rows == 0:
            return [solution]
        
        row_count = min(3, total_rows)
        max_offset = max(total_rows - row_count, 0)
        random_offset = randint(0, max_offset)
        choices_query = f"""
        {base_query}
        LIMIT ? OFFSET ?;
        """
        rows = self._fetchall(choices_query, [*base_params, row_count, random_offset])
        if not rows:
            return [solution]

        proposed_locations = [
            {
                "coordinates": {"lat": row[0], "lon": row[1]},
                "location": self._format_location(*row[2:7]),
                "continent": row[2],
                "details": self._format_location(*row[3:7]),
            }
            for row in rows
        ]
        proposed_locations.insert(randint(0, len(proposed_locations)), solution)
        return proposed_locations

# if __name__ == "__main__":
#     from pprint import pprint
#     challenge = Challenge(continent="Europe")
#     if challenge.url:
#         print("Challenge URL:", challenge.url)
#         print("Solution Details:")
#         pprint(challenge.solution)
#         print("Proposed Locations:")
#         pprint(challenge.proposed_locations)
#     else:
#         print("No challenge found for the specified location filters.")
