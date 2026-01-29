"""
Process tile updates in parallel using multiple connections.
Much faster for large datasets.
"""
import duckdb
import mercantile
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
import math

DB = "data/gbif_plants.duckdb"
Z = 14
CHUNK_SIZE = 100000  # Process 100k rows at a time
NUM_WORKERS = 4  # Number of parallel workers

def process_chunk(chunk_id, offset, limit):
    """Process a chunk of rows in a separate connection."""
    con = duckdb.connect(DB)
    
    # Fetch chunk
    rows = con.execute("""
        SELECT rowid, lat, lon 
        FROM images 
        WHERE lat IS NOT NULL AND lon IS NOT NULL
        LIMIT ? OFFSET ?
    """, [limit, offset]).fetchall()
    
    if not rows:
        con.close()
        return 0
    
    # Calculate tiles
    updates = []
    for rowid, lat, lon in rows:
        t = mercantile.tile(lon, lat, Z)
        updates.append((Z, t.x, t.y, rowid))
    
    # Batch update
    con.execute("BEGIN TRANSACTION")
    con.executemany("UPDATE images SET tile_z=?, tile_x=?, tile_y=? WHERE rowid=?", updates)
    con.execute("COMMIT")
    
    count = len(updates)
    con.close()
    return count

def main():
    print(f"Starting parallel tile update at {datetime.now()}")
    
    # Get total count
    con = duckdb.connect(DB, read_only=True)
    total = con.execute("""
        SELECT COUNT(*) FROM images 
        WHERE lat IS NOT NULL AND lon IS NOT NULL
    """).fetchone()[0]
    con.close()
    
    print(f"Total rows to process: {total:,}")
    print(f"Using {NUM_WORKERS} workers with chunks of {CHUNK_SIZE:,} rows")
    
    # Create chunks
    num_chunks = math.ceil(total / CHUNK_SIZE)
    chunks = [(i, i * CHUNK_SIZE, CHUNK_SIZE) for i in range(num_chunks)]
    
    # Process in parallel
    updated_total = 0
    with ThreadPoolExecutor(max_workers=NUM_WORKERS) as executor:
        futures = {executor.submit(process_chunk, *chunk): chunk for chunk in chunks}
        
        for i, future in enumerate(as_completed(futures), 1):
            count = future.result()
            updated_total += count
            print(f"Chunk {i}/{num_chunks} complete: {count:,} rows ({updated_total:,} total, {updated_total/total*100:.1f}%)")
    
    print(f"\n✓ Updated {updated_total:,} rows")
    print(f"Completed at {datetime.now()}")

if __name__ == "__main__":
    main()
