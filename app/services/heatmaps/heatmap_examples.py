"""
Examples of using the HeatmapGenerator service.

This file demonstrates various ways to use the heatmap generator
for analyzing iNaturalist image distribution data.
"""

from heatmap_generator import HeatmapGenerator
import logging
from pathlib import Path
import os

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Determine the correct database path relative to the project root
# This works whether running from project root or services directory
script_dir = Path(__file__).parent
project_root = script_dir.parent.parent
db_path = project_root / 'data' / 'gbif_plants.duckdb'
output_dir = project_root / 'temp'

# Ensure output directory exists
output_dir.mkdir(exist_ok=True)


def example_1_basic_country_heatmap():
    """Generate a simple heatmap at country level."""
    print("\n" + "="*60)
    print("Example 1: Basic Country Heatmap")
    print("="*60)
    
    generator = HeatmapGenerator(db_path=str(db_path))
    output = generator.generate_scatter_heatmap(
        granularity='country',
        output_path=str(output_dir / 'example1_country.png')
    )
    print(f"✓ Generated: {output}")


def example_2_continent_level():
    """Generate a heatmap at continent level with custom styling."""
    print("\n" + "="*60)
    print("Example 2: Continent Level Analysis")
    print("="*60)
    
    generator = HeatmapGenerator(db_path=str(db_path))
    
    # First, get statistics
    stats = generator.get_statistics('continent')
    print(f"\nContinent Statistics:")
    print(f"  Total continents: {stats['total_regions']}")
    print(f"  Total images: {stats['total_images']:,}")
    for region in stats['top_10_regions']:
        print(f"  - {region['location']}: {region['count']:,}")
    
    # Generate heatmap
    output = generator.generate_scatter_heatmap(
        granularity='continent',
        output_path=str(output_dir / 'example2_continent.png'),
        colormap='plasma',
        figsize=(14, 8),
        title='Global iNaturalist Coverage by Continent'
    )
    print(f"\n✓ Generated: {output}")


def example_3_high_density_cities():
    """Generate heatmap showing only high-density cities."""
    print("\n" + "="*60)
    print("Example 3: High-Density Cities")
    print("="*60)
    
    generator = HeatmapGenerator(db_path=str(db_path))
    
    # Only show cities with at least 1000 images
    output = generator.generate_scatter_heatmap(
        granularity='city',
        min_count=1000,
        output_path=str(output_dir / 'example3_cities_1000plus.png'),
        colormap='viridis',
        title='Cities with 1000+ iNaturalist Images',
        show_labels=True,
        top_n_labels=15
    )
    print(f"✓ Generated: {output}")


def example_4_admin_levels():
    """Compare different administrative levels."""
    print("\n" + "="*60)
    print("Example 4: Administrative Levels Comparison")
    print("="*60)
    
    generator = HeatmapGenerator(db_path=str(db_path))
    
    for granularity in ['admin1', 'admin2']:
        stats = generator.get_statistics(granularity)
        print(f"\n{granularity.upper()} level:")
        print(f"  Regions: {stats['total_regions']}")
        print(f"  Images: {stats['total_images']:,}")
        print(f"  Avg per region: {stats['avg_per_region']:.1f}")
        
        output = generator.generate_scatter_heatmap(
            granularity=granularity,
            min_count=100,
            output_path=str(output_dir / f'example4_{granularity}.png'),
            colormap='RdYlGn',
            show_labels=False
        )
        print(f"  ✓ Generated: {output}")


def example_5_grid_density():
    """Generate a true density heatmap using grid binning."""
    print("\n" + "="*60)
    print("Example 5: Grid-Based Density Heatmap")
    print("="*60)
    
    generator = HeatmapGenerator(db_path=str(db_path))
    
    # High resolution grid
    output = generator.generate_grid_heatmap(
        resolution=200,
        output_path=str(output_dir / 'example5_grid_density.png'),
        colormap='hot',
        log_scale=True,
        title='Global iNaturalist Image Density'
    )
    print(f"✓ Generated: {output}")


def example_6_multi_comparison():
    """Generate a multi-panel comparison of different granularities."""
    print("\n" + "="*60)
    print("Example 6: Multi-Granularity Comparison")
    print("="*60)
    
    generator = HeatmapGenerator(db_path=str(db_path))
    
    output = generator.generate_comparison_heatmaps(
        granularities=['continent', 'country', 'admin1', 'city'],
        output_path=str(output_dir / 'example6_comparison.png'),
        figsize=(20, 14),
        colormap='coolwarm'
    )
    print(f"✓ Generated: {output}")


def example_7_tile_based():
    """Generate heatmap based on map tiles."""
    print("\n" + "="*60)
    print("Example 7: Tile-Based Heatmap")
    print("="*60)
    
    generator = HeatmapGenerator(db_path=str(db_path))
    
    # Get tile statistics
    stats = generator.get_statistics('tile')
    print(f"\nTile Statistics:")
    print(f"  Total tiles with data: {stats['total_regions']}")
    print(f"  Total images: {stats['total_images']:,}")
    
    # Generate heatmap for tiles with significant data
    output = generator.generate_scatter_heatmap(
        granularity='tile',
        min_count=50,
        output_path=str(output_dir / 'example7_tiles.png'),
        colormap='inferno',
        show_labels=False,
        title='Map Tile Coverage (50+ images per tile)'
    )
    print(f"✓ Generated: {output}")


def example_8_custom_colormap():
    """Demonstrate different colormaps."""
    print("\n" + "="*60)
    print("Example 8: Different Colormap Styles")
    print("="*60)
    
    generator = HeatmapGenerator(db_path=str(db_path))
    
    colormaps = ['YlOrRd', 'viridis', 'plasma', 'coolwarm', 'Spectral']
    
    for cmap in colormaps:
        output = generator.generate_scatter_heatmap(
            granularity='country',
            output_path=str(output_dir / f'example8_{cmap}.png'),
            colormap=cmap,
            figsize=(12, 7),
            title=f'iNaturalist Distribution - {cmap} colormap',
            show_labels=False
        )
        print(f"✓ Generated {cmap}: {output}")


def example_9_programmatic_usage():
    """Show how to use the data programmatically without generating images."""
    print("\n" + "="*60)
    print("Example 9: Programmatic Data Access")
    print("="*60)
    
    generator = HeatmapGenerator(db_path=str(db_path))
    
    # Get raw data
    data = generator.get_counts_by_granularity('country', min_count=10000)
    
    print(f"\nCountries with 10,000+ images:")
    for row in data[:15]:
        location, count, lat, lon = row[0], row[1], row[2], row[3]
        print(f"  {location:40} {count:>10,} images (center: {lat:.2f}, {lon:.2f})")
    
    # Get coordinate data for custom analysis
    lon_edges, lat_edges, heatmap = generator.get_coordinate_heatmap_data(resolution=50)
    print(f"\nGrid data dimensions: {heatmap.shape}")
    print(f"Total binned images: {int(heatmap.sum()):,}")
    print(f"Max density in single cell: {int(heatmap.max()):,}")


def main():
    """Run all examples."""
    print("="*60)
    print("Heatmap Generator Examples")
    print("="*60)
    
    examples = [
        ("Basic Country Heatmap", example_1_basic_country_heatmap),
        ("Continent Analysis", example_2_continent_level),
        ("High-Density Cities", example_3_high_density_cities),
        ("Administrative Levels", example_4_admin_levels),
        ("Grid Density", example_5_grid_density),
        ("Multi-Comparison", example_6_multi_comparison),
        ("Tile-Based", example_7_tile_based),
        ("Custom Colormaps", example_8_custom_colormap),
        ("Programmatic Usage", example_9_programmatic_usage),
    ]
    
    print("\nAvailable examples:")
    for i, (name, _) in enumerate(examples, 1):
        print(f"  {i}. {name}")
    
    print("\nOptions:")
    print("  - Run all: python heatmap_examples.py all")
    print("  - Run specific: python heatmap_examples.py 1 3 5")
    print("  - Interactive: python heatmap_examples.py")
    
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == 'all':
            for name, func in examples:
                try:
                    func()
                except Exception as e:
                    print(f"✗ Error in {name}: {e}")
        else:
            # Run specific examples
            for arg in sys.argv[1:]:
                try:
                    idx = int(arg) - 1
                    if 0 <= idx < len(examples):
                        name, func = examples[idx]
                        func()
                    else:
                        print(f"Invalid example number: {arg}")
                except ValueError:
                    print(f"Invalid argument: {arg}")
    else:
        # Interactive mode
        while True:
            choice = input("\nEnter example number (1-9) or 'q' to quit: ").strip()
            if choice.lower() == 'q':
                break
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(examples):
                    name, func = examples[idx]
                    func()
                else:
                    print("Invalid choice. Please enter 1-9.")
            except ValueError:
                print("Please enter a number or 'q'.")


if __name__ == '__main__':
    main()
