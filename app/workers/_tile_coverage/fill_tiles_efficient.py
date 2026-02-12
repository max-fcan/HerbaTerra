"""
Efficient tile coordinate filling using DuckDB Python UDF.
This approach processes millions of rows in seconds instead of hours.
"""
import duckdb
import mercantile
from datetime import datetime

DB = "data/gbif_plants.duckdb"
Z = 14

def tile_x(lon, lat, z):
    """Calculate tile X coordinate."""
    if lon is None or lat is None:
        return None
    return mercantile.tile(lon, lat, z).x

def tile_y(lon, lat, z):
    """Calculate tile Y coordinate."""
    if lon is None or lat is None:
        return None
    return mercantile.tile(lon, lat, z).y

def main():
    print(f"Starting tile update at {datetime.now()}")
    con = duckdb.connect(DB)
    
    # Check how many rows need updating
    count = con.execute("""
        SELECT COUNT(*) FROM images 
        WHERE lat IS NOT NULL AND lon IS NOT NULL
        AND (tile_z IS NULL OR tile_x IS NULL OR tile_y IS NULL)
    """).fetchone()[0]
    print(f"Rows to update: {count:,}")
    
    if count == 0:
        print("All tiles already populated!")
        return
    
    # Create Python UDF functions
    con.create_function("tile_x_udf", tile_x, return_type=duckdb.typing.INTEGER)
    con.create_function("tile_y_udf", tile_y, return_type=duckdb.typing.INTEGER)
    
    # Single UPDATE statement using UDFs - much faster!
    print("Updating tiles (this may take a few minutes)...")
    con.execute(f"""
        UPDATE images
        SET 
            tile_z = {Z},
            tile_x = tile_x_udf(lon, lat, {Z}),
            tile_y = tile_y_udf(lon, lat, {Z})
        WHERE lat IS NOT NULL AND lon IS NOT NULL
        AND (tile_z IS NULL OR tile_x IS NULL OR tile_y IS NULL)
    """)
    
    # Verify
    updated = con.execute("""
        SELECT COUNT(*) FROM images 
        WHERE tile_z = ? AND tile_x IS NOT NULL AND tile_y IS NOT NULL
    """, [Z]).fetchone()[0]
    
    print(f"✓ Updated {updated:,} rows at zoom level {Z}")
    print(f"Completed at {datetime.now()}")
    
    con.close()

if __name__ == "__main__":
    main()
