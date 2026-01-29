import os
import requests
import mercantile
from mapbox_vector_tile import decode as mvt_decode
from dotenv import load_dotenv
from pprint import pprint

load_dotenv()

# -----------------------------
# Configuration
# -----------------------------
TOKEN = os.getenv("MAPILLARY_ACCESS_TOKEN")
if not TOKEN:
    raise RuntimeError("MAPILLARY_ACCESS_TOKEN not set")

# Pick a known urban coordinate with coverage
LAT = 48.8584   # Eiffel Tower
LON = 2.2945
Z = 14

# -----------------------------
# Convert lat/lon to tile
# -----------------------------
tile = mercantile.tile(LON, LAT, Z)
z, x, y = tile.z, tile.x, tile.y

print("Tile selected:")
print(f"  z={z}, x={x}, y={y}")
print()

# -----------------------------
# Fetch vector tile
# -----------------------------
url = (
    f"https://tiles.mapillary.com/maps/vtp/mly1_public/2/"
    f"{z}/{x}/{y}?access_token={TOKEN}"
)

print("Requesting URL:")
print(url)
print()

response = requests.get(url, timeout=20)
response.raise_for_status()

print(f"Raw tile size: {len(response.content)} bytes")
print()

# -----------------------------
# Decode vector tile
# -----------------------------
tile_data = mvt_decode(response.content)

print("Decoded tile keys (layers):")
for layer_name in tile_data.keys():
    print(f"  - {layer_name}")
print()

# -----------------------------
# Detailed layer inspection
# -----------------------------
for layer_name, layer in tile_data.items():
    features = layer.get("features", [])
    extent = layer.get("extent")

    print("=" * 60)
    print(f"LAYER: {layer_name}")
    print(f"Feature count: {len(features)}")
    print(f"Extent: {extent}")
    print()

    if not features:
        print("No features in this layer.")
        continue

    # Geometry types summary
    geom_types = {}
    for f in features:
        g = f.get("geometry", {})
        gtype = g.get("type")
        geom_types[gtype] = geom_types.get(gtype, 0) + 1

    print("Geometry types:")
    for gtype, count in geom_types.items():
        print(f"  {gtype}: {count}")
    print()

    # Inspect first feature in detail
    first = features[0]
    print("First feature (example):")
    print("Geometry:")
    pprint(first.get("geometry"))
    print()
    print("Properties:")
    pprint(first.get("properties"))
    print()

print("=" * 60)
print("Inspection complete.")
