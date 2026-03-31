#!/usr/bin/env python3
"""
Tile generation for Indonesia River Discharge v4 using rasterio.
Properly reprojects to Web Mercator for correct tile display.
Uses v3 YlGnBu color scheme.
"""

import json
from pathlib import Path
import numpy as np

try:
    import xarray as xr
except ImportError:
    print("pip install xarray netcdf4")
    exit(1)

try:
    import rasterio
    from rasterio.io import MemoryFile
    from rasterio.transform import from_origin
    from rasterio.warp import calculate_default_transform, reproject, Resampling
    from rasterio.windows import from_bounds
except ImportError:
    print("pip install rasterio")
    exit(1)

try:
    import mercantile
except ImportError:
    print("pip install mercantile")
    exit(1)

PROJECT_ROOT = Path(__file__).parent.parent
NC_FILE = PROJECT_ROOT / "data_20-29march2026.nc"
OUTPUT_DIR = PROJECT_ROOT / "public" / "data" / "latest" / "tiles"
STYLE_CONFIG = PROJECT_ROOT / "config" / "style.config.json"

NODATA = -9999.0
TILE_SIZE = 256

# Load color stops from config
def load_color_stops():
    with open(STYLE_CONFIG) as f:
        config = json.load(f)
    return config["dischargeColorRamp"]["stops"]


def hex_to_rgb(hex_color: str) -> tuple:
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))


def colorize(values: np.ndarray, stops: list) -> np.ndarray:
    """Convert values to RGBA using color stops."""
    rgba = np.zeros((4, values.shape[0], values.shape[1]), dtype=np.uint8)
    
    valid = np.isfinite(values) & (values > 0) & (values != NODATA)
    if not np.any(valid):
        return rgba
    
    thresholds = np.array([float(stop["value"]) for stop in stops], dtype=float)
    colors = np.array([hex_to_rgb(stop["color"]) for stop in stops], dtype=np.uint8)
    
    # Find color index for each value
    indices = np.searchsorted(thresholds, values, side="right") - 1
    indices = np.clip(indices, 0, len(colors) - 1)
    
    rgba[0, valid] = colors[indices[valid], 0]
    rgba[1, valid] = colors[indices[valid], 1]
    rgba[2, valid] = colors[indices[valid], 2]
    rgba[3, valid] = 210
    
    return rgba


def write_png(path: Path, rgba: np.ndarray):
    """Write RGBA array as PNG using rasterio."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(
        path,
        "w",
        driver="PNG",
        width=rgba.shape[2],
        height=rgba.shape[1],
        count=4,
        dtype="uint8",
    ) as dst:
        dst.write(rgba)


def prepare_mercator_data(values: np.ndarray, lats: np.ndarray, lons: np.ndarray):
    """Reproject data from EPSG:4326 to EPSG:3857 (Web Mercator)."""
    # Build transform for source data
    x_res = float(np.median(np.diff(lons)))
    y_res = float(np.median(np.abs(np.diff(lats))))
    west = float(lons.min() - x_res / 2)
    north = float(lats.max() + y_res / 2)
    src_transform = from_origin(west, north, x_res, y_res)
    
    height, width = values.shape
    
    # Prepare source data
    src_values = np.where(np.isfinite(values), values, NODATA).astype(np.float32)
    
    # Calculate destination transform
    src_bounds = (west, float(lats.min() - y_res / 2), 
                  float(lons.max() + x_res / 2), north)
    
    dst_transform, dst_width, dst_height = calculate_default_transform(
        "EPSG:4326", "EPSG:3857",
        width, height,
        *src_bounds
    )
    
    # Reproject
    dst_values = np.full((dst_height, dst_width), NODATA, dtype=np.float32)
    reproject(
        source=src_values,
        destination=dst_values,
        src_transform=src_transform,
        src_crs="EPSG:4326",
        dst_transform=dst_transform,
        dst_crs="EPSG:3857",
        src_nodata=NODATA,
        dst_nodata=NODATA,
        resampling=Resampling.bilinear,
    )
    
    return dst_values, dst_transform


def generate_tiles_for_date(values: np.ndarray, lats: np.ndarray, lons: np.ndarray,
                            date_str: str, color_stops: list, zoom_levels: list) -> int:
    """Generate tiles for a single date."""
    tile_dir = OUTPUT_DIR / date_str / "control"
    tile_dir.mkdir(parents=True, exist_ok=True)
    
    # Reproject to Web Mercator
    mercator_values, mercator_transform = prepare_mercator_data(values, lats, lons)
    
    # Bounds for Indonesia
    west, south, east, north = 94.0, -12.0, 145.0, 8.0
    
    tile_count = 0
    for zoom in zoom_levels:
        tiles = list(mercantile.tiles(west, south, east, north, [zoom]))
        generated = 0
        
        for tile in tiles:
            xy_bounds = mercantile.xy_bounds(tile)
            window = from_bounds(*xy_bounds, transform=mercator_transform)
            
            # Read tile data
            with MemoryFile() as memfile:
                with memfile.open(
                    driver="GTiff",
                    height=mercator_values.shape[0],
                    width=mercator_values.shape[1],
                    count=1,
                    dtype="float32",
                    crs="EPSG:3857",
                    transform=mercator_transform,
                    nodata=NODATA,
                ) as src:
                    src.write(mercator_values, 1)
                    tile_array = src.read(
                        1,
                        window=window,
                        out_shape=(TILE_SIZE, TILE_SIZE),
                        boundless=True,
                        fill_value=NODATA,
                        resampling=Resampling.bilinear,
                    )
            
            # Skip empty tiles
            valid_count = np.sum((tile_array != NODATA) & np.isfinite(tile_array) & (tile_array > 0))
            if valid_count == 0:
                continue
            
            # Colorize and save
            rgba = colorize(tile_array, color_stops)
            tile_path = tile_dir / str(tile.z) / str(tile.x) / f"{tile.y}.png"
            write_png(tile_path, rgba)
            generated += 1
            tile_count += 1
        
        print(f"    Zoom {zoom}: {generated} tiles")
    
    return tile_count


def main():
    print("=" * 60)
    print("Tile Generation for Indonesia River Discharge v4")
    print("Using rasterio for proper Web Mercator projection")
    print("=" * 60)
    
    # Load color stops
    color_stops = load_color_stops()
    print(f"\nLoaded {len(color_stops)} color stops from config")
    
    # Load dataset
    print(f"\nLoading dataset from {NC_FILE}")
    ds = xr.open_dataset(NC_FILE)
    
    import pandas as pd
    times = pd.to_datetime(ds.valid_time.values, unit='s')
    dates = [t.strftime("%Y-%m-%d") for t in times]
    
    # Limit to 5 dates for faster generation
    dates = dates[-5:]  # Last 5 dates
    print(f"Processing {len(dates)} dates: {dates[0]} to {dates[-1]}")
    
    lats = ds.latitude.values
    lons = ds.longitude.values
    
    zoom_levels = [5, 6, 7]
    total_tiles = 0
    
    for i, date_str in enumerate(dates):
        print(f"\n[{i+1}/{len(dates)}] Processing {date_str}...")
        
        # Find time index for this date
        time_idx = len(ds.valid_time) - len(dates) + i
        values = ds.dis24.isel(valid_time=time_idx).values
        
        count = generate_tiles_for_date(values, lats, lons, date_str, color_stops, zoom_levels)
        total_tiles += count
        print(f"  Generated {count} tiles")
    
    print(f"\n{'=' * 60}")
    print(f"Complete! Generated {total_tiles} tiles")
    print(f"Output: {OUTPUT_DIR}")
    print("=" * 60)


if __name__ == "__main__":
    main()
