import asyncio
import os
import time

import aiohttp
import duckdb
from dotenv import load_dotenv
from mapbox_vector_tile import decode as mvt_decode

load_dotenv()

DB = "data/gbif_plants.duckdb"
Z = 14
TOKEN = os.getenv("MAPILLARY_ACCESS_TOKEN") or os.getenv("MAPILLARY_TOKEN")
if not TOKEN:
    raise RuntimeError("Missing MAPILLARY_ACCESS_TOKEN")

URL = "https://tiles.mapillary.com/maps/vtp/mly1_public/2/{z}/{x}/{y}?access_token={token}"

TILES = int(os.getenv("TILES_TO_PROCESS", "100"))
BATCH_SIZE = int(os.getenv("TILE_BATCH_SIZE", "2000"))

# Mapillary limit: 50,000 requests/minute/app.
MAX_REQUESTS_PER_MINUTE = 50000
SAFETY_FACTOR = float(os.getenv("MAPILLARY_RATE_SAFETY", "0.85"))
SAFE_RPM = max(1.0, MAX_REQUESTS_PER_MINUTE * SAFETY_FACTOR)
SAFE_RPS = SAFE_RPM / 60.0
REQUESTS_PER_SECOND = float(os.getenv("MAPILLARY_RPS", str(SAFE_RPS)))
REQUESTS_PER_SECOND = min(REQUESTS_PER_SECOND, SAFE_RPS)

CONCURRENCY = int(os.getenv("TILE_FETCH_CONCURRENCY", "200"))
REQUEST_TIMEOUT_SECONDS = float(os.getenv("MAPILLARY_REQUEST_TIMEOUT", "20"))
MAX_RETRIES = int(os.getenv("MAPILLARY_MAX_RETRIES", "8"))
BACKOFF_BASE_SECONDS = float(os.getenv("MAPILLARY_BACKOFF_BASE", "0.25"))
BACKOFF_CAP_SECONDS = float(os.getenv("MAPILLARY_BACKOFF_CAP", "5.0"))

if REQUESTS_PER_SECOND <= 0:
    raise RuntimeError("MAPILLARY_RPS must be > 0")
if CONCURRENCY <= 0:
    raise RuntimeError("TILE_FETCH_CONCURRENCY must be > 0")
if BATCH_SIZE <= 0:
    raise RuntimeError("TILE_BATCH_SIZE must be > 0")


class TileFetchError(Exception):
    pass


class AsyncRateLimiter:
    """Global async limiter to keep total request rate under app-level cap."""

    def __init__(self, requests_per_second: float):
        self.interval = 1.0 / requests_per_second
        self._lock = asyncio.Lock()
        self._next_allowed = 0.0

    async def acquire(self) -> None:
        while True:
            async with self._lock:
                now = time.monotonic()
                if now >= self._next_allowed:
                    self._next_allowed = now + self.interval
                    return
                wait_for = self._next_allowed - now
            await asyncio.sleep(wait_for)


def image_count(mvt_bytes: bytes) -> int:
    d = mvt_decode(mvt_bytes)
    layer = d.get("image")
    if not layer:
        return 0
    return len(layer.get("features", []))


async def fetch_tile_with_retry(
    session: aiohttp.ClientSession,
    limiter: AsyncRateLimiter,
    z: int,
    x: int,
    y: int,
) -> bool:
    url = URL.format(z=z, x=x, y=y, token=TOKEN)

    for attempt in range(1, MAX_RETRIES + 1):
        await limiter.acquire()
        try:
            async with session.get(url) as resp:
                if resp.status == 200:
                    body = await resp.read()
                    return image_count(body) > 0

                # Retry transient failures and explicit throttling.
                if resp.status in (429, 500, 502, 503, 504):
                    body = await resp.text()
                    raise TileFetchError(f"{resp.status}: {body[:200]}")

                body = await resp.text()
                raise RuntimeError(f"{resp.status}: {body[:200]}")

        except (aiohttp.ClientError, asyncio.TimeoutError, TileFetchError):
            if attempt == MAX_RETRIES:
                return False
            backoff = min(BACKOFF_CAP_SECONDS, BACKOFF_BASE_SECONDS * (2 ** (attempt - 1)))
            await asyncio.sleep(backoff)
        except Exception:
            return False

    return False


async def fetch_batch(
    rows: list[tuple[int, int]],
    z: int,
    requests_per_second: float,
) -> list[tuple[int, int, bool]]:
    timeout = aiohttp.ClientTimeout(total=REQUEST_TIMEOUT_SECONDS)
    connector = aiohttp.TCPConnector(limit=CONCURRENCY, limit_per_host=CONCURRENCY)
    sem = asyncio.Semaphore(CONCURRENCY)
    limiter = AsyncRateLimiter(requests_per_second)

    async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:
        async def one(x: int, y: int) -> tuple[int, int, bool]:
            async with sem:
                has_coverage = await fetch_tile_with_retry(session, limiter, z, x, y)
                return (x, y, has_coverage)

        tasks = [asyncio.create_task(one(x, y)) for x, y in rows]
        return await asyncio.gather(*tasks)


con = duckdb.connect(DB)

# Only tiles present in the images_with_tiles with no coverage info yet
con.execute("DROP TABLE IF EXISTS tiles_to_check")
con.execute(
    """
    CREATE TEMP TABLE tiles_to_check AS
    SELECT DISTINCT tile_x, tile_y
    FROM images_with_tiles
    WHERE tile_z = ?
      AND tile_x IS NOT NULL
      AND tile_y IS NOT NULL
      AND has_coverage IS NULL
    ORDER BY eventDate DESC
    LIMIT ?;
""",
    [Z, TILES],
)

query_results = con.execute("SELECT COUNT(*) FROM tiles_to_check").fetchone()
TOTAL = query_results[0] if query_results else 0

if TOTAL == 0:
    raise RuntimeError("No tiles found to process")

print(f"Tiles to check: {TOTAL}")
print(f"Batch size: {BATCH_SIZE}")
print(f"Mapillary hard limit: {MAX_REQUESTS_PER_MINUTE:,}/min")
print(f"Configured safe limit: {SAFE_RPM:.0f}/min ({SAFE_RPS:.2f}/sec)")
print(f"Using request rate: {REQUESTS_PER_SECOND:.2f}/sec")
print(f"Concurrency: {CONCURRENCY}")

con.execute(
    """
    CREATE TEMP TABLE IF NOT EXISTS tile_results (
        tile_x INTEGER,
        tile_y INTEGER,
        has_coverage BOOLEAN
    );
"""
)

BATCH_UPDATE = """
UPDATE images
SET has_coverage = t.has_coverage
FROM images_with_tiles i
JOIN tile_results t
  ON i.tile_x = t.tile_x
 AND i.tile_y = t.tile_y
 AND i.tile_z = ?
WHERE images.image_id = i.image_id;
"""

all_tiles = con.execute("SELECT tile_x, tile_y FROM tiles_to_check").fetchall()

processed = 0
batch_index = 0
for start in range(0, len(all_tiles), BATCH_SIZE):
    batch_index += 1
    rows = all_tiles[start : start + BATCH_SIZE]
    print(f"Fetching batch {batch_index}: {len(rows)} rows")

    batch = asyncio.run(fetch_batch(rows, Z, REQUESTS_PER_SECOND))

    processed += len(batch)
    if processed % 200 == 0 or processed == TOTAL:
        print(f"{processed}/{TOTAL}")

    try:
        print(f"Writing batch {batch_index}: {len(batch)} rows")
        con.execute("BEGIN")
        con.executemany("INSERT INTO tile_results VALUES (?, ?, ?)", batch)
        con.execute(BATCH_UPDATE, [Z])
        con.execute("DELETE FROM tile_results")
        con.execute("COMMIT")
        print(f"Committed batch {batch_index}")
    except Exception:
        con.execute("ROLLBACK")
        print("Error during batch update, rolling back")
        raise

print("done")
