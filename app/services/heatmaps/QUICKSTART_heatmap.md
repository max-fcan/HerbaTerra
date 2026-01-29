# Heatmap Generator - Quick Start Guide

## What Was Created

Three new files have been added to `app/services/`:

1. **heatmap_generator.py** - Main service with `HeatmapGenerator` class
2. **heatmap_examples.py** - Comprehensive usage examples
3. **README_heatmap.md** - Full documentation

## Quick Usage

### Command Line

```bash
# Show statistics by country
python app/services/heatmap_generator.py --stats --granularity country

# Generate country-level heatmap
python app/services/heatmap_generator.py --granularity country

# Generate grid-based density heatmap
python app/services/heatmap_generator.py --type grid --resolution 150

# Generate comparison of multiple granularities
python app/services/heatmap_generator.py --type comparison

# Filter to show only high-activity cities
python app/services/heatmap_generator.py --granularity city --min-count 1000
```

### Python Code

```python
from app.services.heatmap_generator import HeatmapGenerator

# Create generator
generator = HeatmapGenerator()

# Generate heatmap at any granularity
output = generator.generate_scatter_heatmap(
    granularity='country',  # or 'continent', 'admin1', 'admin2', 'city', 'tile'
    output_path='my_heatmap.png'
)

# Get statistics
stats = generator.get_statistics('country')
print(f"Total images: {stats['total_images']:,}")
print(f"Top region: {stats['top_10_regions'][0]}")
```

### Run Examples

```bash
# Run specific example
python app/services/heatmap_examples.py 2

# Run all examples
python app/services/heatmap_examples.py all

# Interactive mode
python app/services/heatmap_examples.py
```

## Available Granularities

- **continent**: 7 continents, 17M+ total images
- **country**: 242 countries, 17M+ total images
- **admin1**: State/province level (e.g., California, Ontario)
- **admin2**: County/district level
- **city**: City level
- **tile**: Map tile coordinates (for technical analysis)

## Key Features

✅ Two visualization types: scatter points and grid density
✅ Configurable granularity from continent to city level
✅ Multiple colormap options (YlOrRd, viridis, plasma, hot, etc.)
✅ Statistical analysis of data distribution
✅ Automatic label generation for top regions
✅ Logarithmic scaling for better visualization
✅ Export to PNG with high DPI

## Database Info

The script reads from `data/gbif_plants.duckdb` with the `images` table containing:
- **17,573,005** total plant observation images
- Geographic data: lat/lon, continent, country, admin1, admin2, city
- Top contributor: United States (6.8M images)

## Output Location

By default, heatmaps are saved to the `temp/` directory with descriptive filenames like:
- `heatmap_country.png`
- `heatmap_grid_res150.png`
- `heatmap_comparison.png`

## Next Steps

1. Try different granularities to see patterns at various scales
2. Experiment with colormaps to find the best visualization
3. Use the programmatic API to integrate into your Flask app
4. Check `README_heatmap.md` for full API reference and options

Enjoy exploring your iNaturalist data! 🌍🌱
