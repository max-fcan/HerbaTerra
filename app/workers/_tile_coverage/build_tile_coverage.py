import os, time
import duckdb
import requests
from datetime import datetime, timezone
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from mapbox_vector_tile import decode as mvt_decode

DB = "data/gbif_plants.duckdb"
Z = 14
TOKEN = os.getenv("MAPILLARY_ACCESS_TOKEN") or os.getenv("MAPILLARY_TOKEN")
if not TOKEN:
    raise RuntimeError("Missing MAPILLARY_ACCESS_TOKEN")

URL = "https://tiles.mapillary.com/maps/vtp/mly1_public/2/{z}/{x}/{y}?access_token={token}"

REQUESTS_PER_SECOND = 5
SLEEP = 1.0 / REQUESTS_PER_SECOND

class TileFetchError(Exception): pass

@retry(
    retry=retry_if_exception_type(TileFetchError),
    stop=stop_after_attempt(4),
    wait=wait_exponential(multiplier=0.5, min=0.5, max=8),
)
def _fetch(z, x, y):
    r = requests.get(URL.format(z=z, x=x, y=y, token=TOKEN), timeout=20)
    if r.status_code == 200:
        return r.content
    if r.status_code in (429, 500, 502, 503, 504):
        raise TileFetchError(f"{r.status_code}: {r.text[:200]}")
    raise RuntimeError(f"{r.status_code}: {r.text[:200]}")

def image_count(mvt_bytes: bytes) -> int:
    d = mvt_decode(mvt_bytes)
    layer = d.get("image")
    if not layer:
        return 0
    return len(layer.get("features", []))

con = duckdb.connect(DB)

# Only tiles present in the images_with_tiles with no coverage info yet
tiles = con.execute("""
    SELECT DISTINCT tile_x, tile_y
    FROM images_with_tiles
    WHERE tile_z = ? AND tile_x IS NOT NULL AND tile_y IS NOT NULL AND has_coverage IS NULL
""", [Z]).fetchall()

print(f"Tiles to check: {len(tiles)}")

UPSERT = """
UPDATE images
SET has_coverage = ?
WHERE image_id IN (
    SELECT image_id
    FROM images_with_tiles
    WHERE tile_z = ?
      AND tile_x = ?
      AND tile_y = ?
);
"""


for i, (x, y) in enumerate(tiles, 1):
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    try:
        b = _fetch(Z, x, y)
        cnt = image_count(b)
        con.execute(UPSERT, [cnt > 0, Z, x, y])
    except Exception as e:
        con.execute(UPSERT, [False, Z, x, y])
    if i % 200 == 0:
        print(f"{i}/{len(tiles)}")
    time.sleep(SLEEP)

print("done")
