#!/usr/bin/env python3
"""
Fast tile generation for Indonesia River Discharge Monitoring v4.
Uses vectorized numpy operations for speed.
Color ramp matches v3 (YlGnBu style - green to blue to purple).
"""

import json
import math
from pathlib import Path
import numpy as np

try:
    import xarray as xr
except ImportError:
    print("pip install xarray netcdf4")
    exit(1)

try:
    from PIL import Image
except ImportError:
    print("pip install Pillow")
    exit(1)

try:
    import mercantile
except ImportError:
    print("pip install mercantile")
    exit(1)

PROJECT_ROOT = Path(__file__).parent.parent
NC_FILE = PROJECT_ROOT / "data_20-29march2026.nc"
OUTPUT_DIR = PROJECT_ROOT / "public" / "data" / "latest" / "tiles"

# Color stops matching v3 (green-blue-purple ramp)
COLOR_STOPS = [
    (1, (246, 249, 214)),      # #F6F9D6 - pale yellow-green
    (10, (213, 234, 181)),     # #D5EAB5 - light green
    (25, (168, 214, 167)),     # #A8D6A7 - green
    (50, (111, 183, 174)),     # #6FB7AE - teal
    (100, (62, 145, 181)),     # #3E91B5 - light blue
    (250, (42, 110, 170)),     # #2A6EAA - blue
    (500, (33, 83, 152)),      # #215398 - dark blue
    (1000, (29, 62, 123)),     # #1D3E7B - navy
    (2500, (88, 47, 122)),     # #582F7A - purple
    (5000, (139, 45, 99)),     # #8B2D63 - magenta
    (10000, (183, 55, 59)),    # #B7373B - red
]


def get_color_array(values: np.ndarray) -> np.ndarray:
    """Vectorized color mapping using log scale."""
    h, w = values.shape
    rgba = np.zeros((h, w, 4), dtype=np.uint8)
    
    # Mask for valid values
    valid = ~np.isnan(values) & (values > 0)
    
    if not np.any(valid):
        return rgba
    
    # Log transform for valid values
    log_vals = np.zeros_like(values)
    log_vals[valid] = np.log10(np.clip(values[valid], 1, None))
    
    # Create log thresholds
    log_stops = [(math.log10(max(v, 1)), c) for v, c in COLOR_STOPS]
    
    for i, (log_thresh, color) in enumerate(log_stops):
        if i == 0:
            mask = valid & (log_vals <= log_thresh)
        else:
            prev_log = log_stops[i-1][0]
            mask = valid & (log_vals > prev_log) & (log_vals <= log_thresh)
            
            # Interpolate
            if np.any(mask):
                prev_color = log_stops[i-1][1]
                t = (log_vals[mask] - prev_log) / (log_thresh - prev_log)
                t = np.clip(t, 0, 1)
                for c in range(3):
                    rgba[mask, c] = (prev_color[c] + t * (color[c] - prev_color[c])).astype(np.uint8)
                rgba[mask, 3] = 220
                continue
        
        if np.any(mask):
            rgba[mask, 0] = color[0]
            rgba[mask, 1] = color[1]
            rgba[mask, 2] = color[2]
            rgba[mask, 3] = 220
    
    # Handle values above max
    max_log = log_stops[-1][0]
    max_color = log_stops[-1][1]
    mask = valid & (log_vals > max_log)
    if np.any(mask):
        rgba[mask, 0] = max_color[0]
        rgba[mask, 1] = max_color[1]
        rgba[mask, 2] = max_color[2]
        rgba[mask, 3] = 220
    
    return rgba


def generate_tile(data: np.ndarray, lats: np.ndarray, lons: np.ndarray, 
                  tile: mercantile.Tile, output_path: Path) -> bool:
    """Generate a single tile."""
    bounds = mercantile.bounds(tile)
    
    # Check if tile intersects our data
    lat_min, lat_max = float(lats.min()), float(lats.max())
    lon_min, lon_max = float(lons.min()), float(lons.max())
    
    if (bounds.east < lon_min or bounds.west > lon_max or
        bounds.north < lat_min or bounds.south > lat_max):
        return False
    
    # Create pixel coordinate arrays
    px = np.arange(256)
    py = np.arange(256)
    
    # Convert pixel coordinates to lat/lon
    pixel_lons = bounds.west + (px / 256) * (bounds.east - bounds.west)
    pixel_lats = bounds.north - (py / 256) * (bounds.north - bounds.south)
    
    # Create meshgrid
    lon_grid, lat_grid = np.meshgrid(pixel_lons, pixel_lats)
    
    # Find nearest grid indices
    lat_indices = np.abs(lats[:, np.newaxis, np.newaxis] - lat_grid).argmin(axis=0)
    lon_indices = np.abs(lons[:, np.newaxis, np.newaxis] - lon_grid).argmin(axis=0)
    
    # Sample data
    tile_data = data[lat_indices, lon_indices]
    
    # Mask out-of-bounds pixels
    out_of_bounds = ((lat_grid < lat_min) | (lat_grid > lat_max) | 
                     (lon_grid < lon_min) | (lon_grid > lon_max))
    tile_data[out_of_bounds] = np.nan
    
    # Check if tile has any valid data
    if np.all(np.isnan(tile_data)):
        return False
    
    # Convert to colors
    rgba = get_color_array(tile_data)
    
    # Save tile
    output_path.parent.mkdir(parents=True, exist_ok=True)
    img = Image.fromarray(rgba, 'RGBA')
    img.save(output_path, 'PNG', optimize=True)
    
    return True


def generate_tiles_for_date(ds: xr.Dataset, time_idx: int, date_str: str, 
                            zoom_levels: list = [5, 6, 7]) -> int:
    """Generate all tiles for a specific date."""
    # Use "control" subfolder like v3
    tiles_dir = OUTPUT_DIR / date_str / "control"
    tiles_dir.mkdir(parents=True, exist_ok=True)
    
    data = ds.dis24.isel(valid_time=time_idx).values
    lats = ds.latitude.values
    lons = ds.longitude.values
    
    lat_min, lat_max = float(lats.min()), float(lats.max())
    lon_min, lon_max = float(lons.min()), float(lons.max())
    
    tile_count = 0
    
    for z in zoom_levels:
        tiles = list(mercantile.tiles(lon_min, lat_min, lon_max, lat_max, zooms=z))
        print(f"    Zoom {z}: {len(tiles)} tiles...", end=" ", flush=True)
        
        generated = 0
        for tile in tiles:
            tile_path = tiles_dir / str(z) / str(tile.x) / f"{tile.y}.png"
            if generate_tile(data, lats, lons, tile, tile_path):
                generated += 1
                tile_count += 1
        
        print(f"{generated} generated")
    
    return tile_count


def main():
    print("=" * 60)
    print("Tile Generation for Indonesia River Discharge v4")
    print("=" * 60)
    
    print(f"\nLoading dataset from {NC_FILE}")
    ds = xr.open_dataset(NC_FILE)
    
    import pandas as pd
    times = pd.to_datetime(ds.valid_time.values, unit='s')
    dates = [t.strftime("%Y-%m-%d") for t in times]
    print(f"Found {len(dates)} dates: {dates[0]} to {dates[-1]}")
    
    total_tiles = 0
    
    for i, date_str in enumerate(dates):
        print(f"\n[{i+1}/{len(dates)}] Processing {date_str}...")
        count = generate_tiles_for_date(ds, i, date_str)
        total_tiles += count
        print(f"  Generated {count} tiles for {date_str}")
    
    print(f"\n{'=' * 60}")
    print(f"Complete! Generated {total_tiles} tiles total.")
    print(f"Output: {OUTPUT_DIR}")
    print("=" * 60)


if __name__ == "__main__":
    main()
