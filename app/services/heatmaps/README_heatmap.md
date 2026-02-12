# Heatmap Generator Service

A comprehensive Python service for generating geographic heatmaps from iNaturalist plant observation data stored in a DuckDB database.

## Features

- **Multiple Granularity Levels**: Generate heatmaps at different geographic scales
  - Continent
  - Country
  - Admin Level 1 (states/provinces)
  - Admin Level 2 (counties/districts)
  - City
  - Map tiles

- **Two Heatmap Types**:
  - **Scatter Heatmap**: Shows discrete geographic regions as colored points
  - **Grid Heatmap**: True density heatmap using 2D binning

- **Customization Options**:
  - Multiple colormaps
  - Adjustable figure sizes
  - Logarithmic or linear scaling
  - Label display for top regions
  - Minimum count filtering

- **Statistical Analysis**: Get detailed statistics about data distribution

## Installation

The required dependencies are already in `requirements.txt`:
- duckdb
- matplotlib
- numpy

## Quick Start

### Command Line Usage

The service can be used directly from the command line:

```bash
# Generate a country-level heatmap
python app/services/heatmap_generator.py --granularity country

# Generate a grid-based density heatmap
python app/services/heatmap_generator.py --type grid --resolution 200

# Get statistics for a specific granularity
python app/services/heatmap_generator.py --stats --granularity city

# Generate comparison of multiple granularities
python app/services/heatmap_generator.py --type comparison

# Filter by minimum count
python app/services/heatmap_generator.py --granularity city --min-count 1000
```

#### Command Line Options

- `--granularity`: Geographic level (continent, country, admin1, admin2, city, tile)
- `--type`: Heatmap type (scatter, grid, comparison)
- `--output`: Output file path
- `--resolution`: Grid resolution for grid type (default: 100)
- `--min-count`: Minimum image count to include (default: 1)
- `--stats`: Print statistics instead of generating heatmap
- `--db-path`: Path to DuckDB database (default: data/gbif_plants.duckdb)

### Python API Usage

```python
from app.services.heatmap_generator import HeatmapGenerator

# Initialize the generator
generator = HeatmapGenerator()

# Generate a scatter heatmap at country level
output = generator.generate_scatter_heatmap(
    granularity='country',
    output_path='my_heatmap.png'
)

# Generate a grid-based density heatmap
output = generator.generate_grid_heatmap(
    resolution=150,
    output_path='density_map.png',
    colormap='hot',
    log_scale=True
)

# Get statistics
stats = generator.get_statistics('country')
print(f"Total images: {stats['total_images']}")
print(f"Total countries: {stats['total_regions']}")

# Generate comparison heatmap
output = generator.generate_comparison_heatmaps(
    granularities=['continent', 'country', 'admin1', 'city'],
    output_path='comparison.png'
)

# Access raw data
data = generator.get_counts_by_granularity('country', min_count=1000)
for row in data:
    location, count, avg_lat, avg_lon = row[0], row[1], row[2], row[3]
    print(f"{location}: {count} images")
```

## Examples

See `heatmap_examples.py` for comprehensive examples:

```bash
# Run all examples
python app/services/heatmap_examples.py all

# Run specific examples
python app/services/heatmap_examples.py 1 3 5

# Interactive mode
python app/services/heatmap_examples.py
```

### Example 1: Basic Country Heatmap

```python
generator = HeatmapGenerator()
output = generator.generate_scatter_heatmap(
    granularity='country',
    output_path='country_heatmap.png'
)
```

### Example 2: High-Resolution Density Map

```python
generator = HeatmapGenerator()
output = generator.generate_grid_heatmap(
    resolution=200,
    output_path='density_map.png',
    colormap='hot',
    log_scale=True
)
```

### Example 3: Cities with High Activity

```python
generator = HeatmapGenerator()
output = generator.generate_scatter_heatmap(
    granularity='city',
    min_count=1000,  # Only cities with 1000+ images
    show_labels=True,
    top_n_labels=15
)
```

### Example 4: Custom Styling

```python
generator = HeatmapGenerator()
output = generator.generate_scatter_heatmap(
    granularity='country',
    colormap='viridis',
    figsize=(20, 12),
    title='Custom Styled Heatmap'
)
```

## API Reference

### HeatmapGenerator Class

#### Methods

##### `__init__(db_path='data/gbif_plants.duckdb')`
Initialize the generator with database path.

##### `get_counts_by_granularity(granularity, min_count=1)`
Get image counts grouped by specified granularity.

**Parameters:**
- `granularity`: Geographic level (continent, country, admin1, admin2, city, tile)
- `min_count`: Minimum count to include

**Returns:** List of tuples `(location_name, count, avg_lat, avg_lon)`

##### `generate_scatter_heatmap(...)`
Generate scatter-based heatmap on world map.

**Parameters:**
- `granularity`: Geographic level
- `min_count`: Minimum image count
- `output_path`: Save path (auto-generates if None)
- `figsize`: Figure size tuple (width, height)
- `colormap`: Matplotlib colormap name
- `title`: Custom title
- `show_labels`: Whether to show location labels
- `top_n_labels`: Number of top locations to label

**Returns:** Path to generated image

##### `generate_grid_heatmap(...)`
Generate grid-based density heatmap.

**Parameters:**
- `resolution`: Grid resolution (bins per dimension)
- `output_path`: Save path
- `figsize`: Figure size tuple
- `colormap`: Matplotlib colormap name
- `title`: Custom title
- `log_scale`: Use logarithmic color scale

**Returns:** Path to generated image

##### `generate_comparison_heatmaps(...)`
Generate multi-panel comparison at different granularities.

**Parameters:**
- `granularities`: List of granularities to compare
- `output_path`: Save path
- `figsize`: Figure size tuple
- `colormap`: Matplotlib colormap name

**Returns:** Path to generated image

##### `get_statistics(granularity='country')`
Get statistics about data distribution.

**Returns:** Dictionary with statistics including:
- `total_regions`: Number of regions
- `total_images`: Total image count
- `avg_per_region`: Average images per region
- `median_per_region`: Median images per region
- `std_per_region`: Standard deviation
- `min_count`, `max_count`: Min/max counts
- `top_10_regions`: Top 10 regions with counts

##### `get_coordinate_heatmap_data(resolution=100)`
Get raw coordinate data binned into 2D grid.

**Returns:** Tuple of `(lon_edges, lat_edges, heatmap_counts)`

## Colormap Options

Popular matplotlib colormaps for heatmaps:
- `'YlOrRd'`: Yellow to Orange to Red (default for scatter)
- `'hot'`: Black to Red to Yellow to White (default for grid)
- `'viridis'`: Perceptually uniform blue to yellow
- `'plasma'`: Purple to Pink to Yellow
- `'coolwarm'`: Blue to White to Red
- `'RdYlGn'`: Red to Yellow to Green
- `'Spectral'`: Rainbow colors
- `'inferno'`: Dark purple to yellow

## Database Schema

The service reads from the `images` table with the following relevant columns:
- `lat`, `lon`: Geographic coordinates
- `continent`: Continent name
- `country`: Country name
- `admin1`: First-level administrative division (state/province)
- `admin2`: Second-level administrative division (county/district)
- `city`: City name
- `tile_z`, `tile_x`, `tile_y`: Map tile coordinates

## Output Files

By default, heatmaps are saved to the `temp/` directory with descriptive names:
- `heatmap_country.png`: Scatter heatmap at country level
- `heatmap_grid_res100.png`: Grid heatmap at resolution 100
- `heatmap_comparison.png`: Multi-panel comparison

## Performance Tips

1. **Grid Resolution**: Higher resolution (200+) provides better detail but takes longer
2. **Minimum Count**: Use `min_count` to filter out low-activity regions and reduce clutter
3. **Database Connection**: The generator uses read-only connections for safety
4. **Large Datasets**: For large datasets, consider using the grid heatmap with moderate resolution

## Integration with Flask App

To integrate with your Flask application:

```python
from flask import send_file
from app.services.heatmap_generator import HeatmapGenerator

@app.route('/api/heatmap/<granularity>')
def get_heatmap(granularity):
    generator = HeatmapGenerator()
    output = generator.generate_scatter_heatmap(
        granularity=granularity,
        output_path=f'temp/heatmap_{granularity}.png'
    )
    return send_file(output, mimetype='image/png')
```

## Troubleshooting

### No data appears on heatmap
- Check database has data: `--stats` to see counts
- Reduce `min_count` parameter
- Verify granularity field has data in database

### Image quality issues
- Increase `figsize` for larger images
- Increase `dpi` in `plt.savefig()` call (default is 150)
- Use higher grid resolution for grid heatmaps

### Memory issues with high resolution
- Reduce grid resolution (try 100 or 150)
- Use scatter heatmap instead of grid
- Filter data with higher `min_count`

## License

Part of the HerbaTerra project.
