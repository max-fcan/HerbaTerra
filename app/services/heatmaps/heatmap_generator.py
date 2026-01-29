"""
Heatmap Generator Service
Generates heatmaps showing iNaturalist image counts by different geographic granularities.
"""

import duckdb
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Literal
import logging

logger = logging.getLogger(__name__)

# Define granularity types
GranularityType = Literal['continent', 'country', 'admin1', 'admin2', 'city', 'tile']


class HeatmapGenerator:
    """Generate heatmaps from iNaturalist image data at various geographic granularities."""
    
    def __init__(self, db_path: str = 'data/gbif_plants.duckdb'):
        """
        Initialize the heatmap generator.
        
        Args:
            db_path: Path to the DuckDB database file
        """
        self.db_path = db_path
        
    def get_counts_by_granularity(
        self, 
        granularity: GranularityType,
        min_count: int = 1
    ) -> List[Tuple]:
        """
        Get image counts grouped by specified granularity.
        
        Args:
            granularity: The geographic level to aggregate by
            min_count: Minimum count to include in results
            
        Returns:
            List of tuples containing (location_name, count, avg_lat, avg_lon)
        """
        conn = duckdb.connect(self.db_path, read_only=True)
        
        try:
            if granularity == 'tile':
                # For tile granularity, use tile coordinates
                query = """
                    SELECT 
                        CONCAT('z', tile_z, '_x', tile_x, '_y', tile_y) AS location,
                        COUNT(*) as count,
                        AVG(lat) as avg_lat,
                        AVG(lon) as avg_lon,
                        tile_z,
                        tile_x,
                        tile_y
                    FROM images
                    WHERE tile_z IS NOT NULL 
                        AND tile_x IS NOT NULL 
                        AND tile_y IS NOT NULL
                    GROUP BY tile_z, tile_x, tile_y
                    HAVING COUNT(*) >= ?
                    ORDER BY count DESC
                """
                results = conn.execute(query, [min_count]).fetchall()
            else:
                # For other granularities, group by the specified field
                query = f"""
                    SELECT 
                        {granularity},
                        COUNT(*) as count,
                        AVG(lat) as avg_lat,
                        AVG(lon) as avg_lon
                    FROM images
                    WHERE {granularity} IS NOT NULL 
                        AND {granularity} != ''
                        AND lat IS NOT NULL 
                        AND lon IS NOT NULL
                    GROUP BY {granularity}
                    HAVING COUNT(*) >= ?
                    ORDER BY count DESC
                """
                results = conn.execute(query, [min_count]).fetchall()
                
            return results
            
        finally:
            conn.close()
    
    def get_coordinate_heatmap_data(
        self, 
        resolution: int = 100
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Get raw coordinate data binned into a 2D grid for true heatmap visualization.
        
        Args:
            resolution: Number of bins per dimension (creates resolution x resolution grid)
            
        Returns:
            Tuple of (lon_edges, lat_edges, heatmap_counts)
        """
        conn = duckdb.connect(self.db_path, read_only=True)
        
        try:
            # Fetch all coordinates
            query = """
                SELECT lon, lat 
                FROM images 
                WHERE lat IS NOT NULL 
                    AND lon IS NOT NULL
                    AND lat BETWEEN -90 AND 90
                    AND lon BETWEEN -180 AND 180
            """
            results = conn.execute(query).fetchall()
            
            if not results:
                logger.warning("No valid coordinates found in database")
                return np.array([]), np.array([]), np.array([[]])
            
            lons, lats = zip(*results)
            
            # Create 2D histogram
            heatmap, lon_edges, lat_edges = np.histogram2d(
                lons, lats, 
                bins=resolution,
                range=[[-180, 180], [-90, 90]]
            )
            
            return lon_edges, lat_edges, heatmap
            
        finally:
            conn.close()
    
    def generate_scatter_heatmap(
        self,
        granularity: GranularityType = 'country',
        min_count: int = 1,
        output_path: Optional[str] = None,
        figsize: Tuple[int, int] = (16, 9),
        colormap: str = 'YlOrRd',
        title: Optional[str] = None,
        show_labels: bool = True,
        top_n_labels: int = 20
    ) -> str:
        """
        Generate a scatter-based heatmap on a world map projection.
        Each point represents a geographic region colored by image count.
        
        Args:
            granularity: Geographic level (continent, country, admin1, admin2, city, tile)
            min_count: Minimum image count to include
            output_path: Path to save the image (if None, auto-generates)
            figsize: Figure size in inches
            colormap: Matplotlib colormap name
            title: Custom title (if None, auto-generates)
            show_labels: Whether to show location labels
            top_n_labels: Number of top locations to label
            
        Returns:
            Path to the generated heatmap image
        """
        logger.info(f"Generating scatter heatmap with granularity: {granularity}")
        
        # Get data
        data = self.get_counts_by_granularity(granularity, min_count)
        
        if not data:
            raise ValueError(f"No data found for granularity '{granularity}' with min_count={min_count}")
        
        # Parse data based on whether it's tile or location data
        if granularity == 'tile':
            locations = [row[0] for row in data]
            counts = [row[1] for row in data]
            lats = [row[2] for row in data]
            lons = [row[3] for row in data]
        else:
            locations = [row[0] for row in data]
            counts = [row[1] for row in data]
            lats = [row[2] for row in data]
            lons = [row[3] for row in data]
        
        # Create figure
        fig, ax = plt.subplots(figsize=figsize, facecolor='white')
        
        # Normalize counts for color mapping
        counts_array = np.array(counts)
        norm = mcolors.LogNorm(vmin=max(1, counts_array.min()), vmax=counts_array.max())
        
        # Create scatter plot
        scatter = ax.scatter(
            lons, lats,
            c=counts,
            cmap=colormap,
            norm=norm,
            s=100,  # Point size
            alpha=0.7,
            edgecolors='black',
            linewidth=0.5
        )
        
        # Add colorbar
        cbar = plt.colorbar(scatter, ax=ax, label='Image Count')
        cbar.ax.tick_params(labelsize=10)
        
        # Add labels for top locations
        if show_labels and top_n_labels > 0:
            for i in range(min(top_n_labels, len(locations))):
                ax.annotate(
                    f"{locations[i]}\n({counts[i]})",
                    xy=(lons[i], lats[i]),
                    xytext=(5, 5),
                    textcoords='offset points',
                    fontsize=8,
                    alpha=0.7,
                    bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.6, edgecolor='none')
                )
        
        # Set map extent
        ax.set_xlim(-180, 180)
        ax.set_ylim(-90, 90)
        ax.set_aspect('equal')
        
        # Add grid
        ax.grid(True, alpha=0.3, linestyle='--', linewidth=0.5)
        ax.set_axisbelow(True)
        
        # Labels
        ax.set_xlabel('Longitude', fontsize=12)
        ax.set_ylabel('Latitude', fontsize=12)
        
        # Title
        if title is None:
            title = f'iNaturalist Image Distribution by {granularity.capitalize()}'
        ax.set_title(title, fontsize=16, fontweight='bold', pad=20)
        
        # Add statistics
        total_images = sum(counts)
        stats_text = f'Total: {total_images:,} images | {len(locations)} {granularity}s'
        ax.text(
            0.02, 0.98, stats_text,
            transform=ax.transAxes,
            fontsize=10,
            verticalalignment='top',
            bbox=dict(boxstyle='round,pad=0.5', facecolor='white', alpha=0.8)
        )
        
        plt.tight_layout()
        
        # Save figure
        if output_path is None:
            output_dir = Path('temp')
            output_dir.mkdir(exist_ok=True)
            output_path = output_dir / f'heatmap_{granularity}.png'
        
        plt.savefig(output_path, dpi=150, bbox_inches='tight', facecolor='white')
        plt.close()
        
        logger.info(f"Heatmap saved to: {output_path}")
        return str(output_path)
    
    def generate_grid_heatmap(
        self,
        resolution: int = 100,
        output_path: Optional[str] = None,
        figsize: Tuple[int, int] = (16, 9),
        colormap: str = 'hot',
        title: Optional[str] = None,
        log_scale: bool = True
    ) -> str:
        """
        Generate a true grid-based heatmap showing density of observations.
        
        Args:
            resolution: Grid resolution (higher = more detailed)
            output_path: Path to save the image
            figsize: Figure size in inches
            colormap: Matplotlib colormap name
            title: Custom title
            log_scale: Whether to use logarithmic color scale
            
        Returns:
            Path to the generated heatmap image
        """
        logger.info(f"Generating grid heatmap with resolution: {resolution}")
        
        # Get binned data
        lon_edges, lat_edges, heatmap = self.get_coordinate_heatmap_data(resolution)
        
        if heatmap.size == 0:
            raise ValueError("No valid coordinate data found")
        
        # Create figure
        fig, ax = plt.subplots(figsize=figsize, facecolor='white')
        
        # Prepare data for plotting
        if log_scale:
            # Add 1 to avoid log(0)
            plot_data = np.log10(heatmap.T + 1)
            cbar_label = 'log₁₀(Image Count + 1)'
        else:
            plot_data = heatmap.T
            cbar_label = 'Image Count'
        
        # Create heatmap
        im = ax.imshow(
            plot_data,
            extent=[-180, 180, -90, 90],
            origin='lower',
            cmap=colormap,
            aspect='auto',
            interpolation='bilinear'
        )
        
        # Add colorbar
        cbar = plt.colorbar(im, ax=ax, label=cbar_label)
        cbar.ax.tick_params(labelsize=10)
        
        # Add grid
        ax.grid(True, alpha=0.3, linestyle='--', linewidth=0.5, color='white')
        ax.set_axisbelow(False)
        
        # Labels
        ax.set_xlabel('Longitude', fontsize=12)
        ax.set_ylabel('Latitude', fontsize=12)
        
        # Title
        if title is None:
            title = f'iNaturalist Image Density Heatmap'
        ax.set_title(title, fontsize=16, fontweight='bold', pad=20)
        
        # Add statistics
        total_images = int(heatmap.sum())
        non_zero_cells = np.count_nonzero(heatmap)
        stats_text = f'Total: {total_images:,} images | {non_zero_cells} active cells'
        ax.text(
            0.02, 0.98, stats_text,
            transform=ax.transAxes,
            fontsize=10,
            verticalalignment='top',
            color='white',
            bbox=dict(boxstyle='round,pad=0.5', facecolor='black', alpha=0.7)
        )
        
        plt.tight_layout()
        
        # Save figure
        if output_path is None:
            output_dir = Path('temp')
            output_dir.mkdir(exist_ok=True)
            output_path = output_dir / f'heatmap_grid_res{resolution}.png'
        
        plt.savefig(output_path, dpi=150, bbox_inches='tight', facecolor='white')
        plt.close()
        
        logger.info(f"Grid heatmap saved to: {output_path}")
        return str(output_path)
    
    def generate_comparison_heatmaps(
        self,
        granularities: List[GranularityType] = None,
        output_path: Optional[str] = None,
        figsize: Tuple[int, int] = (20, 12),
        colormap: str = 'YlOrRd'
    ) -> str:
        """
        Generate a multi-panel comparison of heatmaps at different granularities.
        
        Args:
            granularities: List of granularities to compare (default: all major ones)
            output_path: Path to save the image
            figsize: Figure size in inches
            colormap: Matplotlib colormap name
            
        Returns:
            Path to the generated comparison image
        """
        if granularities is None:
            granularities = ['continent', 'country', 'admin1', 'city']
        
        logger.info(f"Generating comparison heatmaps for: {granularities}")
        
        n_plots = len(granularities)
        n_cols = 2
        n_rows = (n_plots + n_cols - 1) // n_cols
        
        fig, axes = plt.subplots(n_rows, n_cols, figsize=figsize, facecolor='white')
        axes = axes.flatten() if n_plots > 1 else [axes]
        
        for idx, granularity in enumerate(granularities):
            ax = axes[idx]
            
            # Get data
            data = self.get_counts_by_granularity(granularity, min_count=1)
            
            if not data:
                ax.text(0.5, 0.5, f'No data for {granularity}', 
                       ha='center', va='center', transform=ax.transAxes)
                continue
            
            # Parse data
            locations = [row[0] for row in data]
            counts = [row[1] for row in data]
            lats = [row[2] for row in data]
            lons = [row[3] for row in data]
            
            # Normalize counts
            counts_array = np.array(counts)
            norm = mcolors.LogNorm(vmin=max(1, counts_array.min()), vmax=counts_array.max())
            
            # Scatter plot
            scatter = ax.scatter(
                lons, lats,
                c=counts,
                cmap=colormap,
                norm=norm,
                s=50,
                alpha=0.7,
                edgecolors='black',
                linewidth=0.3
            )
            
            # Colorbar
            cbar = plt.colorbar(scatter, ax=ax, label='Count')
            cbar.ax.tick_params(labelsize=8)
            
            # Formatting
            ax.set_xlim(-180, 180)
            ax.set_ylim(-90, 90)
            ax.set_aspect('equal')
            ax.grid(True, alpha=0.3, linestyle='--', linewidth=0.5)
            ax.set_title(
                f'{granularity.capitalize()} ({len(locations)} regions, {sum(counts):,} images)',
                fontsize=12,
                fontweight='bold'
            )
            ax.set_xlabel('Longitude', fontsize=10)
            ax.set_ylabel('Latitude', fontsize=10)
        
        # Hide unused subplots
        for idx in range(n_plots, len(axes)):
            axes[idx].set_visible(False)
        
        plt.suptitle('iNaturalist Image Distribution Comparison', 
                     fontsize=16, fontweight='bold', y=0.995)
        plt.tight_layout()
        
        # Save
        if output_path is None:
            output_dir = Path('temp')
            output_dir.mkdir(exist_ok=True)
            output_path = output_dir / 'heatmap_comparison.png'
        
        plt.savefig(output_path, dpi=150, bbox_inches='tight', facecolor='white')
        plt.close()
        
        logger.info(f"Comparison heatmap saved to: {output_path}")
        return str(output_path)
    
    def get_statistics(self, granularity: GranularityType = 'country') -> Dict:
        """
        Get statistics about the data at a given granularity.
        
        Args:
            granularity: Geographic level to analyze
            
        Returns:
            Dictionary with statistics
        """
        data = self.get_counts_by_granularity(granularity, min_count=1)
        
        if not data:
            return {'error': f'No data found for granularity: {granularity}'}
        
        counts = [row[1] for row in data]
        locations = [row[0] for row in data]
        
        return {
            'granularity': granularity,
            'total_regions': len(locations),
            'total_images': sum(counts),
            'avg_per_region': np.mean(counts),
            'median_per_region': np.median(counts),
            'std_per_region': np.std(counts),
            'min_count': min(counts),
            'max_count': max(counts),
            'top_10_regions': [
                {'location': locations[i], 'count': counts[i]} 
                for i in range(min(10, len(locations)))
            ]
        }


def main():
    """Example usage of the heatmap generator."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Generate heatmaps from iNaturalist image data'
    )
    parser.add_argument(
        '--granularity',
        type=str,
        default='country',
        choices=['continent', 'country', 'admin1', 'admin2', 'city', 'tile'],
        help='Geographic granularity level'
    )
    parser.add_argument(
        '--type',
        type=str,
        default='scatter',
        choices=['scatter', 'grid', 'comparison'],
        help='Type of heatmap to generate'
    )
    parser.add_argument(
        '--output',
        type=str,
        help='Output file path'
    )
    parser.add_argument(
        '--resolution',
        type=int,
        default=100,
        help='Grid resolution (for grid type only)'
    )
    parser.add_argument(
        '--min-count',
        type=int,
        default=1,
        help='Minimum image count to include'
    )
    parser.add_argument(
        '--stats',
        action='store_true',
        help='Print statistics instead of generating heatmap'
    )
    parser.add_argument(
        '--db-path',
        type=str,
        default='data/gbif_plants.duckdb',
        help='Path to DuckDB database'
    )
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    generator = HeatmapGenerator(db_path=args.db_path)
    
    if args.stats:
        # Print statistics
        stats = generator.get_statistics(args.granularity)
        print(f"\n{'='*60}")
        print(f"Statistics for {stats['granularity']}")
        print(f"{'='*60}")
        print(f"Total regions: {stats['total_regions']}")
        print(f"Total images: {stats['total_images']:,}")
        print(f"Average per region: {stats['avg_per_region']:.1f}")
        print(f"Median per region: {stats['median_per_region']:.1f}")
        print(f"Std dev per region: {stats['std_per_region']:.1f}")
        print(f"Min count: {stats['min_count']}")
        print(f"Max count: {stats['max_count']}")
        print(f"\nTop 10 regions:")
        for item in stats['top_10_regions']:
            print(f"  {item['location']}: {item['count']:,}")
    else:
        # Generate heatmap
        if args.type == 'scatter':
            output = generator.generate_scatter_heatmap(
                granularity=args.granularity,
                min_count=args.min_count,
                output_path=args.output
            )
        elif args.type == 'grid':
            output = generator.generate_grid_heatmap(
                resolution=args.resolution,
                output_path=args.output
            )
        elif args.type == 'comparison':
            output = generator.generate_comparison_heatmaps(
                output_path=args.output
            )
        
        print(f"\nHeatmap generated: {output}")


if __name__ == '__main__':
    main()
