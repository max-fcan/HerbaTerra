"""
Benchmark reverse geocoding performance to estimate processing time.

To run this benchmark, use the command:
    python -m app.workers._reverse_geocoding.benchmark_rg
"""

import csv
import time
from pathlib import Path

### --- Create csv file using following command: --- ###

# CREATE TEMP TABLE unique_coords AS
# SELECT DISTINCT lat, lon
# FROM images
# WHERE lat IS NOT NULL AND lon IS NOT NULL;
 
# COPY unique_coords TO 'coords.csv' (HEADER, DELIMITER ',');

### ------------------------------------------------ ###

COORDINATES_CSV_PATH = "C:/Users/maxen/Desktop/GITHUB_REPOSITORIES/HerbaTerra/temp/0004570-260120142942310/coords.csv"

def main():
    """Benchmark reverse geocoding with different batch sizes and sample counts."""
    from app.services.location_tags import reverse_geocode_many
    
    # Load sample coordinates
    coords_file = Path(COORDINATES_CSV_PATH)
    
    print("Loading sample coordinates for benchmarking...")
    coords = []
    with open(coords_file, newline="", mode="r") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            coords.append((float(row["lat"]), float(row["lon"])))
            if i >= 499999:  # Load 500k for testing
                break
    
    total_coords = i + 1
    print(f"Loaded {total_coords:,} sample coordinates\n")
    
    # Test configurations
    test_configs = [
        (500000, 80000), # 500k coords, batch 80k (full test)
        (500000, 100000),# 500k coords, batch 100k
        (500000, 150000), # 500k coords, batch 150k
        (500000, 200000), # 500k coords, batch 200k
    ]
    
    print("=" * 80)
    print(f"{'Sample Size':>12} | {'Batch Size':>10} | {'Time (s)':>9} | {'Rate (c/s)':>11} | {'Est. 8M (min)':>15}")
    print("=" * 80)
    
    results = []
    
    for sample_size, batch_size in test_configs:
        if sample_size > total_coords:
            continue
            
        sample = coords[:sample_size]
        
        # Run benchmark
        start = time.time()
        processed = {}
        
        for i in range(0, len(sample), batch_size):
            batch = sample[i : i + batch_size]
            tagged = reverse_geocode_many(batch)
            processed.update(tagged)
        
        elapsed = time.time() - start
        rate = sample_size / elapsed
        est_time_8m = (8_000_000 / rate) / 60  # in minutes
        
        results.append({
            'sample_size': sample_size,
            'batch_size': batch_size,
            'elapsed': elapsed,
            'rate': rate,
            'est_8m': est_time_8m
        })
        
        print(f"{sample_size:>12,} | {batch_size:>10,} | {elapsed:>9.2f} | {rate:>11.1f} | {est_time_8m:>15.1f}")
    
    print("=" * 80)
    
    # Show recommendation
    if results:
        best = max(results, key=lambda x: x['rate'])
        print(f"\n✓ RECOMMENDED CONFIGURATION:")
        print(f"  Batch Size: {best['batch_size']:,}")
        print(f"  Expected Rate: {best['rate']:.0f} coords/second")
        print(f"  Estimated Time for 8M: {best['est_8m']:.1f} minutes ({best['est_8m']/60:.1f} hours)")
        
        print(f"\n💡 RANGE ESTIMATE for 8M coordinates:")
        min_time = min(r['est_8m'] for r in results)
        max_time = max(r['est_8m'] for r in results)
        print(f"  Best case:  {min_time:.0f} minutes ({min_time/60:.1f} hours)")
        print(f"  Worst case: {max_time:.0f} minutes ({max_time/60:.1f} hours)")


if __name__ == '__main__':
    main()
