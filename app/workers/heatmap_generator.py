"""Generate a heatmap visualization of iNaturalist observations on a world map."""

from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


def fetch_coordinates(db_path: str | Path) -> tuple[list[float], list[float]]:
    """Fetch latitude and longitude from observations."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT latitude, longitude 
        FROM observations 
        WHERE latitude IS NOT NULL 
          AND longitude IS NOT NULL
    """)
    
    coords = cursor.fetchall()
    conn.close()
    
    if not coords:
        print("No coordinates found in database", file=sys.stderr)
        sys.exit(1)
    
    lats = [c[0] for c in coords]
    lons = [c[1] for c in coords]
    
    print(f"Loaded {len(coords)} observations")
    return lats, lons


def create_heatmap_simple(
    lats: list[float],
    lons: list[float],
    output_path: str | Path,
    bins: int = 200,
    title: str = "iNaturalist Observation Heatmap",
) -> None:
    """Create a simple heatmap using matplotlib histogram2d."""
    fig, ax = plt.subplots(figsize=(16, 10), dpi=150)
    
    # Create 2D histogram
    h, xedges, yedges, img = ax.hist2d(
        lons, 
        lats,
        bins=bins,
        cmap='hot',
        cmin=1,  # Don't show bins with 0 observations
    )
    
    # Add colorbar
    cbar = plt.colorbar(img, ax=ax, label='Number of Observations')
    
    # Set labels and title
    ax.set_xlabel('Longitude', fontsize=12)
    ax.set_ylabel('Latitude', fontsize=12)
    ax.set_title(title, fontsize=16, pad=20)
    
    # Set world map bounds
    ax.set_xlim(-180, 180)
    ax.set_ylim(-90, 90)
    
    # Add grid
    ax.grid(True, alpha=0.3, linestyle='--', linewidth=0.5)
    
    # Add statistics text
    stats_text = f"Total observations: {len(lats)}\n"
    stats_text += f"Lat range: [{min(lats):.2f}, {max(lats):.2f}]\n"
    stats_text += f"Lon range: [{min(lons):.2f}, {max(lons):.2f}]"
    
    ax.text(
        0.02, 0.98, 
        stats_text,
        transform=ax.transAxes,
        fontsize=10,
        verticalalignment='top',
        bbox=dict(boxstyle='round', facecolor='white', alpha=0.8)
    )
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    print(f"Heatmap saved to {output_path}")
    plt.close()


def create_heatmap_cartopy(
    lats: list[float],
    lons: list[float],
    output_path: str | Path,
    bins: int = 200,
    title: str = "iNaturalist Observation Heatmap",
) -> None:
    """Create a heatmap with proper map projection using cartopy."""
    try:
        import cartopy.crs as ccrs
        import cartopy.feature as cfeature
    except ImportError:
        print("cartopy not available, falling back to simple heatmap")
        create_heatmap_simple(lats, lons, output_path, bins, title)
        return
    
    fig = plt.figure(figsize=(20, 12), dpi=150)
    ax = plt.axes(projection=ccrs.Robinson())
    
    # Add map features
    ax.add_feature(cfeature.LAND, facecolor='lightgray', edgecolor='none', alpha=0.3)
    ax.add_feature(cfeature.OCEAN, facecolor='lightblue', alpha=0.2)
    ax.add_feature(cfeature.COASTLINE, linewidth=0.5, edgecolor='gray')
    ax.add_feature(cfeature.BORDERS, linewidth=0.3, edgecolor='gray', alpha=0.5)
    ax.set_global()
    
    # Create 2D histogram data
    H, xedges, yedges = np.histogram2d(lons, lats, bins=bins, range=[[-180, 180], [-90, 90]])
    
    # Mask zero values
    H = np.ma.masked_where(H == 0, H)
    
    # Plot heatmap
    extent = [xedges[0], xedges[-1], yedges[0], yedges[-1]]
    img = ax.imshow(
        H.T,
        extent=extent,
        origin='lower',
        cmap='hot',
        alpha=0.7,
        transform=ccrs.PlateCarree(),
        interpolation='gaussian'
    )
    
    # Add colorbar
    cbar = plt.colorbar(img, ax=ax, label='Number of Observations', shrink=0.6)
    
    ax.set_title(title, fontsize=18, pad=20)
    
    # Add statistics text
    stats_text = f"Total observations: {len(lats)}"
    ax.text(
        0.02, 0.98, 
        stats_text,
        transform=ax.transAxes,
        fontsize=12,
        verticalalignment='top',
        bbox=dict(boxstyle='round', facecolor='white', alpha=0.8)
    )
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    print(f"Heatmap saved to {output_path}")
    plt.close()


def main():
    parser = argparse.ArgumentParser(
        description="Generate a heatmap of iNaturalist observations on a world map"
    )
    parser.add_argument(
        "--db",
        type=str,
        default="temp/inat_test.db",
        help="Path to SQLite database (default: temp/inat_test.db)"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="temp/observation_heatmap.png",
        help="Output PNG file path (default: temp/observation_heatmap.png)"
    )
    parser.add_argument(
        "--bins",
        type=int,
        default=200,
        help="Number of bins for heatmap grid (default: 200)"
    )
    parser.add_argument(
        "--title",
        type=str,
        default="iNaturalist Observation Heatmap",
        help="Chart title"
    )
    parser.add_argument(
        "--simple",
        action="store_true",
        help="Use simple matplotlib plot instead of cartopy"
    )
    
    args = parser.parse_args()
    
    # Fetch coordinates
    lats, lons = fetch_coordinates(args.db)
    
    # Create output directory if needed
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Generate heatmap
    if args.simple:
        create_heatmap_simple(lats, lons, output_path, args.bins, args.title)
    else:
        create_heatmap_cartopy(lats, lons, output_path, args.bins, args.title)


if __name__ == "__main__":
    main()
