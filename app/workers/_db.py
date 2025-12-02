from dataclasses import dataclass
import sqlite3
from pathlib import Path
from typing import Optional, Dict, Any

from app.logging_config import configure_logging

LOGGER: Any = configure_logging(
    name="db_worker",
    log_filename="db_worker.log",
)
DB_PATH = Path("data/mapillary_images.db")

_DB_COLUMNS = {
    ("image_id", "TEXT PRIMARY KEY"),
    ("lon", "REAL NOT NULL"),
    ("lat", "REAL NOT NULL"),
    # Unix epoch milliseconds from Mapillary (captured_at)
    ("captured_at", "INTEGER"),
    # Booleans represented as 0/1 integers with validation
    ("has_plant", "INTEGER NOT NULL DEFAULT 0 CHECK (has_plant IN (0,1)),"),
    # Location tags
    ("continent", "TEXT"),
    ("country_name", "TEXT"),
    ("admin1", "TEXT"),
    ("admin2", "TEXT"),
    ("city", "TEXT"),
}

@dataclass
class MapillaryImage:
    """
    Represents a Mapillary image with relevant attributes.
    """
    image_id: str
    lon: float
    lat: float
    captured_at: Optional[int] = None
    has_plant: bool = False
    plant_labels: Optional[str] = None
    continent: Optional[str] = None
    country: Optional[str] = None
    admin1: Optional[str] = None
    admin2: Optional[str] = None
    city: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "image_id": self.image_id,
            "lon": self.lon,
            "lat": self.lat,
            "captured_at": self.captured_at,
            "has_plant": self.has_plant,
            "plant_labels": self.plant_labels,
            "continent": self.continent,
            "country": self.country,
            "admin1": self.admin1,
            "admin2": self.admin2,
            "city": self.city,
        }


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db() -> None:
    cx = get_connection()
    cu = cx.cursor()

    query = f"""
        CREATE TABLE IF NOT EXISTS auctions (
            {', '.join(f'{name} {type_}' for name, type_ in _DB_COLUMNS)}
        )
    """
    
    LOGGER.debug("Executing SQL query: %s", query)
    cu.execute(query)

    cx.commit()
    cx.close()


def insert_images(
    images: list[MapillaryImage]
) -> None:
    """
    Insert or refresh one image row (upsert by image_id).
    """
    cx = get_connection()
    cu = cx.cursor()

    cu.executemany(
        """
        INSERT INTO images (
            image_id,
            lon,
            lat,
            captured_at,
            has_plant,
            plant_labels,
            continent,
            country_name,
            admin1,
            admin2,
            city
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(image_id) DO UPDATE SET
            lon = excluded.lon,
            lat = excluded.lat,
            captured_at = excluded.captured_at,
            has_plant = excluded.has_plant,
            plant_labels = excluded.plant_labels,
            continent = excluded.continent,
            country_name = excluded.country_name,
            admin1 = excluded.admin1,
            admin2 = excluded.admin2,
            city = excluded.city
        """,
        [(img.image_id, img.lon, img.lat, img.captured_at, img.has_plant, img.plant_labels, img.continent, img.country, img.admin1, img.admin2, img.city) for img in images]
    )

    cx.commit()
    cx.close()


if __name__ == "__main__":
    init_db()
    print("DB initialized at", DB_PATH)
