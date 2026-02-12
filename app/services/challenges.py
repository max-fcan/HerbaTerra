import duckdb
from random import randint

class Challenge:
    def __init__(self, continent: str | None = None, country: str | None = None, admin1: str | None = None, admin2: str | None = None, city: str | None = None):
        self.conn = self.connect_to_db()
        
        result = self.get_plant_sample(continent, country, admin1, admin2, city)
        if result is None:
            self.url = None
            self.solution = None
            self.proposed_locations = None
            self.conn.close()
            return
        
        self.url, self.solution = result
        self.proposed_locations = self.get_proposed_locations(self.solution)
        
        self.conn.close()

    def connect_to_db(self):
        return duckdb.connect("data/gbif_plants.duckdb")
    
    def get_plant_sample(self, continent: str | None = None, country: str | None = None, admin1: str | None = None, admin2: str | None = None, city: str | None = None) -> tuple | None:
        # Use duckdb to get challenge URL based on location filters
        query = """
        SELECT image_url, lat, lon, continent, country, admin1, admin2, city
        FROM images
        WHERE
            (? IS NULL OR continent = ?) AND
            (? IS NULL OR country = ?) AND          
            (? IS NULL OR admin1 = ?) AND
            (? IS NULL OR admin2 = ?) AND
            (? IS NULL OR city = ?)
        ORDER BY RANDOM()
        LIMIT 1;
        """
        # Execute query with provided filters and return a random image URL
        result: tuple[float, float, str, str, str, str, str] | None = self.conn.execute(query, [continent.upper(), continent.upper(), country, country, admin1, admin1, admin2, admin2, city, city]).fetchone()
        if not result:
            return None
        return (result[0], {'coordinates': {'lat': result[1], 'lon': result[2]}, 'location': self._format_location(*result[3:8])})
    
    def _format_location(self, *tags) -> str:
        def _camel_case(s: str) -> str:
            return ' '.join(word.capitalize() for word in s.split(' '))
        
        length = len(tags)
        
        parts = [
            tags[0] if length > 0 else '',  # continent
            tags[1] if length > 1 else '',  # country
            tags[2] if length > 2 else '',  # admin1
            tags[3] if length > 3 else '',  # admin2
            tags[4] if length > 4 else ''   # city
        ]
        return ', '.join([_camel_case(part) for part in parts if part])
    
    def get_proposed_locations(self, solution: dict) -> list[dict]:
        # Use duckdb to get proposed locations near the solution coordinates
        query = """
        SELECT DISTINCT lat, lon, continent, country, admin1, admin2, city
        FROM images
        WHERE CONTINENT IS NOT NULL AND COUNTRY IS NOT NULL
        AND lat IS NOT NULL AND lon IS NOT NULL
          AND NOT (lat = ? AND lon = ?)
        ORDER BY RANDOM()
        LIMIT 3;
        """
        results: list[tuple[float, float, str, str, str, str, str]] | None = self.conn.execute(query, [solution['coordinates']['lat'], solution['coordinates']['lon']]).fetchall()
        if not results:
            return [solution]
        
        proposed_locations = [({'coordinates': {'lat': r[0], 'lon': r[1]}, 'location': self._format_location(*r[2:7])}) for r in results]
        proposed_locations.insert(randint(0, len(results)), solution)
        
        return proposed_locations

if __name__ == "__main__":
    from pprint import pprint
    challenge = Challenge(continent="Europe")
    if challenge.url:
        print("Challenge URL:", challenge.url)
        print("Solution Details:")
        pprint(challenge.solution)
        print("Proposed Locations:")
        pprint(challenge.proposed_locations)
    else:
        print("No challenge found for the specified location filters.")