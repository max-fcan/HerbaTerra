"""
Reverse geocoding worker using DuckDB for efficient coordinate processing.

To run this worker, use the command: 
    python -m app.workers._reverse_geocoding.rg_duckdb
"""

import csv
import duckdb
import time
from pathlib import Path

COORDINATES_CSV_PATH = r"C:/Users/maxen/Desktop/GITHUB_REPOSITORIES/HerbaTerra/temp/0004570-260120142942310/coords.csv"

TAGGED_COORDS_CSV_PATH = r"C:/Users/maxen/Desktop/GITHUB_REPOSITORIES/HerbaTerra/temp/0004570-260120142942310/coord_tags.csv"

def main():
    """Main execution function for reverse geocoding coordinates."""
    from app.services.location_tags import reverse_geocode_many
    
    # Load coordinates
    coords = []
    print("Loading coordinates from CSV...")
    start_load = time.time()
    with open(Path(COORDINATES_CSV_PATH), newline="", mode="r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            coords.append((float(row["lat"]), float(row["lon"])))
    
    load_time = time.time() - start_load
    print(f"Loaded {len(coords):,} coordinates in {load_time:.2f}s")
    print(f"Sample coordinates: {coords[:3]}")

    # Reverse geocode in batches
    BATCH_SIZE = 200_000  # Optimized for performance
    results = {}
    total_batches = (len(coords) + BATCH_SIZE - 1) // BATCH_SIZE
    
    print(f"\nStarting reverse geocoding with batch size {BATCH_SIZE:,}")
    print(f"Total batches: {total_batches:,}")
    print(f"Estimated time: {(len(coords) / (8_000_000 / (2 * 3600))):.1f} - {(len(coords) / (8_000_000 / (20 * 3600))):.1f} minutes\n") # Estimate a total of 2min to 20min for a 8M coords run with 200k batch size
    
    start_time = time.time()
    last_report = start_time

    for i in range(0, len(coords), BATCH_SIZE):
        batch = coords[i : i + BATCH_SIZE]
        batch_num = i // BATCH_SIZE + 1
        
        batch_start = time.time()
        tagged = reverse_geocode_many(batch)
        results.update(tagged)
        batch_time = time.time() - batch_start
        
        # Progress report every 10 batches or 30 seconds
        current_time = time.time()
        if batch_num % 5 == 0 or (current_time - last_report) > 30:
            elapsed = current_time - start_time
            processed = i + len(batch)
            progress = (processed / len(coords)) * 100
            rate = processed / elapsed if elapsed > 0 else 0
            remaining = (len(coords) - processed) / rate if rate > 0 else 0
            
            print(f"Batch {batch_num}/{total_batches} | "
                  f"Progress: {progress:.1f}% ({processed:,}/{len(coords):,}) | "
                  f"Rate: {rate:.0f} coords/s | "
                  f"Elapsed: {elapsed/60:.1f}m | "
                  f"ETA: {remaining/60:.1f}m")
            last_report = current_time
    
    total_time = time.time() - start_time
    print(f"\n✓ Reverse geocoding complete in {total_time/60:.1f} minutes")
    print(f"  Average rate: {len(coords)/total_time:.0f} coords/s")

    # Persist results
    print("\nWriting results to CSV...")
    write_start = time.time()
    with open(Path(TAGGED_COORDS_CSV_PATH), "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["lat", "lon", "continent", "country", "admin1", "admin2", "city", "error"],
        )
        writer.writeheader()
        for (lat, lon), tags in results.items():
            writer.writerow({
                "lat": lat,
                "lon": lon,
                **tags,
            })
    
    write_time = time.time() - write_start
    print(f"✓ Results written in {write_time:.2f}s")
    print(f"\nTotal execution time: {(time.time() - start_load)/60:.1f} minutes")

if __name__ == '__main__':
    main()
