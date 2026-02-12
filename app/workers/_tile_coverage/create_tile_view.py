"""
Use GENERATED columns to compute tiles on-the-fly (DuckDB 0.9+).
This is the BEST approach - no storage overhead, always up-to-date.
"""
import duckdb

DB = "data/gbif_plants.duckdb"
Z = 14

# Note: DuckDB supports computed columns via expressions
# But for complex calculations, we can create a view or use UDFs in queries

con = duckdb.connect(DB)

# Option A: Create a view with tiles computed on-the-fly
con.execute("""
    CREATE OR REPLACE VIEW images_with_tiles AS
    SELECT 
        *,
        14 as tile_z,
        CAST(FLOOR((lon + 180.0) / 360.0 * POW(2, 14)) AS INTEGER) as tile_x,
        CAST(FLOOR((1.0 - ln(tan(radians(lat)) + 1.0 / cos(radians(lat))) / pi()) / 2.0 * POW(2, 14)) AS INTEGER) as tile_y
    FROM images
    WHERE lat IS NOT NULL AND lon IS NOT NULL
""")

print("✓ Created view 'images_with_tiles' with computed tile coordinates")
print("Usage: SELECT * FROM images_with_tiles WHERE tile_x = ? AND tile_y = ?")

# Test it
sample = con.execute("SELECT image_id, lat, lon, tile_x, tile_y FROM images_with_tiles LIMIT 5").fetchdf()
print("\nSample rows:")
print(sample)

con.close()
