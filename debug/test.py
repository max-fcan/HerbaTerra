import os
import time
import math
import duckdb
import requests
import mercantile
from datetime import datetime, timezone
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from mapbox_vector_tile import decode as mvt_decode


# -----------------------------
# 1) Configuration
# -----------------------------
MAPILLARY_TOKEN = os.getenv("MAPILLARY_ACCESS_TOKEN") or os.getenv("MAPILLARY_TOKEN")
if not MAPILLARY_TOKEN:
    raise RuntimeError("Missing MAPILLARY_ACCESS_TOKEN (or MAPILLARY_TOKEN) in environment variables.")

DUCKDB_PATH = os.getenv("DUCKDB_PATH", r"c:\users\maxen\desktop\GITHUB_REPOSITORIES\HerbaTerra\data\gbif_plants.duckdb")

# Mapillary vector tile endpoint pattern (z/x/y)
TILE_URL = "https://tiles.mapillary.com/maps/vtp/mly1_public/2/{z}/{x}/{y}?access_token={token}"

# Use z=14 as a practical coverage zoom
Z = 14

# Politeness: keep requests slow enough to avoid hammering Mapillary
REQUESTS_PER_SECOND = 5
SLEEP_SECONDS = 1.0 / REQUESTS_PER_SECOND


# -----------------------------
# 2) DuckDB schema
# -----------------------------
CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS mapillary_tile_coverage (
  z SMALLINT,
  x INTEGER,
  y INTEGER,
  has_coverage BOOLEAN,
  image_point_count INTEGER,
  last_checked_at TIMESTAMP,
  status VARCHAR,         -- 'ok' | 'error'
  last_error VARCHAR,
  PRIMARY KEY (z, x, y)
);
"""


# -----------------------------
# 3) Network fetching with retries
# -----------------------------
class TileFetchError(Exception):
    pass


@retry(
    retry=retry_if_exception_type(TileFetchError),
    stop=stop_after_attempt(4),
    wait=wait_exponential(multiplier=0.5, min=0.5, max=8),
)
def fetch_tile_bytes(z: int, x: int, y: int) -> bytes:
    """
    Downloads raw MVT bytes for one tile.
    Retries on transient failures.
    """
    url = TILE_URL.format(z=z, x=x, y=y, token=MAPILLARY_TOKEN)
    r = requests.get(url, timeout=20)

    # Common failure modes:
    # 403: token invalid / not passed as query param
    # 429: rate limited
    # 5xx: transient server issues
    if r.status_code == 200:
        return r.content

    if r.status_code in (429, 500, 502, 503, 504):
        raise TileFetchError(f"Transient HTTP {r.status_code}: {r.text[:200]}")

    # Non-retryable errors
    raise RuntimeError(f"Non-retryable HTTP {r.status_code}: {r.text[:200]}")


def count_image_points(mvt_bytes: bytes) -> int:
    """
    Decodes the vector tile and counts features in layer 'image'.
    If layer doesn't exist, count is 0.
    """
    tile = mvt_decode(mvt_bytes)  # dict: {layer_name: {features: [...] ...}, ...}
    layer = tile.get("image")
    if not layer:
        return 0
    features = layer.get("features", [])
    return len(features)


# -----------------------------
# 4) Tile selection from plant coords
# -----------------------------
def iter_tiles_from_duckdb(con: duckdb.DuckDBPyConnection, limit: int = 100):
    """
    Pull lat/lon from your plants table and yield unique (z,x,y) tiles.

    Adjust the SQL to match your real table/column names.
    """
    sql = """
    SELECT lat, lon
    FROM images
    WHERE lat IS NOT NULL AND lon IS NOT NULL
    LIMIT ?
    """
    rows = con.execute(sql, [limit]).fetchall()

    seen = set()
    for lat, lon in rows:
        t = mercantile.tile(lon, lat, Z)
        key = (Z, t.x, t.y)
        if key not in seen:
            seen.add(key)
            yield key


# -----------------------------
# 5) Upsert results into DuckDB
# -----------------------------
UPSERT_SQL = """
INSERT INTO mapillary_tile_coverage
(z, x, y, has_coverage, image_point_count, last_checked_at, status, last_error)
VALUES (?, ?, ?, ?, ?, ?, ?, ?)
ON CONFLICT (z, x, y) DO UPDATE SET
  has_coverage = excluded.has_coverage,
  image_point_count = excluded.image_point_count,
  last_checked_at = excluded.last_checked_at,
  status = excluded.status,
  last_error = excluded.last_error
"""


def main():
    con = duckdb.connect(DUCKDB_PATH)
    con.execute(CREATE_TABLE_SQL)

    tiles = list(iter_tiles_from_duckdb(con, limit=20000))
    print(f"Unique tiles to check: {len(tiles)}")

    checked = 0
    ok = 0
    covered = 0

    for z, x, y in tiles:
        checked += 1
        now = datetime.now(timezone.utc).replace(tzinfo=None)  # DuckDB TIMESTAMP friendly

        try:
            mvt_bytes = fetch_tile_bytes(z, x, y)
            point_count = count_image_points(mvt_bytes)
            has_cov = point_count > 0

            con.execute(
                UPSERT_SQL,
                [z, x, y, has_cov, point_count, now, "ok", None]
            )

            ok += 1
            if has_cov:
                covered += 1

        except Exception as e:
            # Record the failure. This tile is "unknown" until later.
            con.execute(
                UPSERT_SQL,
                [z, x, y, False, 0, now, "error", str(e)[:500]]
            )

        if checked % 200 == 0:
            print(f"Checked {checked}/{len(tiles)} | ok={ok} | covered={covered}")

        time.sleep(SLEEP_SECONDS)

    print(f"Done. Checked={checked}, ok={ok}, covered={covered}")


if __name__ == "__main__":
    main()
