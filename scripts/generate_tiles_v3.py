"""
Tile generator for Indonesia River Discharge v4
Following exact v3 approach with proper Web Mercator projection
"""
from __future__ import annotations

import json
from pathlib import Path

import mercantile
import numpy as np
import rasterio
import xarray as xr
from rasterio.enums import Resampling
from rasterio.io import MemoryFile
from rasterio.mask import mask
from rasterio.transform import from_origin
from rasterio.warp import calculate_default_transform, reproject
from rasterio.windows import from_bounds
from shapely.geometry import mapping, shape
from shapely.ops import unary_union

# Configuration
REPO_ROOT = Path(__file__).resolve().parent.parent
NC_FILE = REPO_ROOT / "data_20-29march2026.nc"
OUTPUT_DIR = REPO_ROOT / "public" / "data" / "latest" / "tiles"
STYLE_CONFIG = REPO_ROOT / "config" / "style.config.json"
BOUNDARY_FILE = REPO_ROOT / "public" / "data" / "latest" / "boundaries" / "provinces.geojson"

NODATA_VALUE = -9999.0
TILE_SIZE = 256
ZOOM_LEVELS = [4, 5, 6, 7, 8]
BOUNDS = {"west": 94.0, "south": -12.0, "east": 145.0, "north": 8.0}


def load_color_stops():
    """Load color stops from style config"""
    with open(STYLE_CONFIG) as f:
        config = json.load(f)
    stops = config["dischargeColorRamp"]["stops"]
    print(f"Loaded {len(stops)} color stops from config")
    return stops


def load_indonesia_boundary():
    """Load Indonesia boundary for clipping"""
    if BOUNDARY_FILE.exists():
        with open(BOUNDARY_FILE) as f:
            geojson = json.load(f)
        geometries = [shape(feature["geometry"]) for feature in geojson["features"]]
        return unary_union(geometries)
    else:
        # Fallback: use a simple bounding box
        from shapely.geometry import box
        return box(BOUNDS["west"], BOUNDS["south"], BOUNDS["east"], BOUNDS["north"])


def build_transform(longitudes: np.ndarray, latitudes: np.ndarray):
    """Build geotransform from coordinate arrays - exactly like v3"""
    x_res = float(np.median(np.diff(longitudes)))
    y_res = float(np.median(np.diff(latitudes)))
    if np.all(np.diff(latitudes) < 0):
        y_res = abs(y_res)
    else:
        y_res = abs(y_res)
    west = float(longitudes.min() - x_res / 2)
    north = float(latitudes.max() + y_res / 2)
    return from_origin(west, north, x_res, y_res)


def colorize(values: np.ndarray, stops: list[dict]) -> np.ndarray:
    """Colorize values array using threshold stops - exactly like v3"""
    rgba = np.zeros((4, values.shape[0], values.shape[1]), dtype=np.uint8)
    rgba[3, :, :] = 0  # Start with full transparency

    valid = np.isfinite(values) & (values > 0) & (values != NODATA_VALUE)
    if not np.any(valid):
        return rgba

    thresholds = np.array([float(stop["value"]) for stop in stops], dtype=float)
    colors = np.array(
        [
            [int(str(stop["color"])[1:3], 16), int(str(stop["color"])[3:5], 16), int(str(stop["color"])[5:7], 16)]
            for stop in stops
        ],
        dtype=np.uint8,
    )

    indices = np.searchsorted(thresholds, values, side="right") - 1
    indices = np.clip(indices, 0, len(colors) - 1)

    rgba[0, valid] = colors[indices[valid], 0]
    rgba[1, valid] = colors[indices[valid], 1]
    rgba[2, valid] = colors[indices[valid], 2]
    rgba[3, valid] = 210  # Semi-transparent
    return rgba


def write_png(path: Path, rgba: np.ndarray) -> None:
    """Write RGBA array to PNG file"""
    path.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(
        path,
        "w",
        driver="PNG",
        width=rgba.shape[2],
        height=rgba.shape[1],
        count=4,
        dtype="uint8",
    ) as dataset:
        dataset.write(rgba)


def prepare_mercator_dataset(values: np.ndarray, lats: np.ndarray, lons: np.ndarray, adm0_geom):
    """
    Prepare a Web Mercator reprojected dataset - exactly like v3
    
    This function:
    1. Creates a GeoTIFF in EPSG:4326 with proper transform
    2. Clips to Indonesia boundary
    3. Reprojects to EPSG:3857 (Web Mercator)
    """
    transform = build_transform(lons, lats)
    height, width = values.shape
    
    print(f"  Input: {height}x{width}, lon: {lons.min():.3f} to {lons.max():.3f}, lat: {lats.min():.3f} to {lats.max():.3f}")
    print(f"  Resolution: {np.median(np.diff(lons)):.4f}° x {np.median(np.diff(lats)):.4f}°")

    with MemoryFile() as memory_file:
        with memory_file.open(
            driver="GTiff",
            height=height,
            width=width,
            count=1,
            dtype="float32",
            crs="EPSG:4326",
            transform=transform,
            nodata=NODATA_VALUE,
        ) as dataset:
            # Write data, converting NaN to NODATA
            data = np.where(np.isfinite(values), values, NODATA_VALUE).astype("float32")
            dataset.write(data, 1)
            
            # Clip to Indonesia boundary
            clipped, clipped_transform = mask(dataset, [mapping(adm0_geom)], crop=True, nodata=NODATA_VALUE)
            clipped_bounds = rasterio.transform.array_bounds(clipped.shape[1], clipped.shape[2], clipped_transform)
    
    print(f"  Clipped bounds: {clipped_bounds}")
    
    # Calculate transform for Web Mercator projection
    dest_transform, dest_width, dest_height = calculate_default_transform(
        "EPSG:4326",
        "EPSG:3857",
        clipped.shape[2],
        clipped.shape[1],
        *clipped_bounds,
    )
    
    print(f"  Mercator output: {dest_height}x{dest_width}")

    # Reproject to Web Mercator
    destination = np.full((dest_height, dest_width), NODATA_VALUE, dtype=np.float32)
    reproject(
        source=clipped[0],
        destination=destination,
        src_transform=clipped_transform,
        src_crs="EPSG:4326",
        dst_transform=dest_transform,
        dst_crs="EPSG:3857",
        src_nodata=NODATA_VALUE,
        dst_nodata=NODATA_VALUE,
        resampling=Resampling.bilinear,
    )

    return destination, dest_transform


def generate_tiles_for_date(date_str: str, values: np.ndarray, lats: np.ndarray, lons: np.ndarray, 
                            adm0_geom, color_stops: list[dict]) -> int:
    """Generate all tiles for a single date"""
    
    # Prepare mercator dataset (this is the key step from v3)
    mercator_values, mercator_transform = prepare_mercator_dataset(values, lats, lons, adm0_geom)
    
    tile_dir = OUTPUT_DIR / date_str / "control"
    tile_count = 0
    
    west, south, east, north = BOUNDS["west"], BOUNDS["south"], BOUNDS["east"], BOUNDS["north"]
    
    for zoom in ZOOM_LEVELS:
        zoom_count = 0
        for tile in mercantile.tiles(west, south, east, north, [zoom]):
            # Get tile bounds in Web Mercator coordinates
            xy_bounds = mercantile.xy_bounds(tile)
            window = from_bounds(*xy_bounds, transform=mercator_transform)
            
            # Read tile data from the mercator raster
            with MemoryFile() as memory_file:
                with memory_file.open(
                    driver="GTiff",
                    height=mercator_values.shape[0],
                    width=mercator_values.shape[1],
                    count=1,
                    dtype="float32",
                    crs="EPSG:3857",
                    transform=mercator_transform,
                    nodata=NODATA_VALUE,
                ) as dataset:
                    dataset.write(mercator_values, 1)
                    tile_array = dataset.read(
                        1,
                        window=window,
                        out_shape=(TILE_SIZE, TILE_SIZE),
                        boundless=True,
                        fill_value=NODATA_VALUE,
                        resampling=Resampling.bilinear,
                    )
            
            # Colorize and write PNG
            rgba = colorize(tile_array, color_stops)
            write_png(tile_dir / str(tile.z) / str(tile.x) / f"{tile.y}.png", rgba)
            tile_count += 1
            zoom_count += 1
        
        print(f"    Zoom {zoom}: {zoom_count} tiles")
    
    return tile_count


def main():
    print("=" * 60)
    print("Tile Generation for Indonesia River Discharge v4")
    print("Following exact v3 approach with proper Web Mercator projection")
    print("=" * 60)
    print()
    
    # Load configuration
    color_stops = load_color_stops()
    adm0_geom = load_indonesia_boundary()
    
    # Load NetCDF data
    print(f"\nLoading dataset from {NC_FILE}")
    ds = xr.open_dataset(NC_FILE)
    
    # Get coordinate arrays
    lons = ds.longitude.values
    lats = ds.latitude.values
    times = ds.valid_time.values  # Historical data uses valid_time
    
    print(f"Dataset shape: {ds.dis24.shape}")
    print(f"Longitude range: {lons.min():.3f} to {lons.max():.3f} ({len(lons)} points)")
    print(f"Latitude range: {lats.min():.3f} to {lats.max():.3f} ({len(lats)} points)")
    print(f"Resolution: {np.median(np.diff(lons)):.4f}° x {abs(np.median(np.diff(lats))):.4f}°")
    print(f"Time steps: {len(times)}")
    
    # Process all available historical dates
    import pandas as pd
    dates = [pd.Timestamp(t).strftime("%Y-%m-%d") for t in times]
    dates_to_process = dates
    
    print(f"\nProcessing {len(dates_to_process)} dates: {dates_to_process[0]} to {dates_to_process[-1]}")
    print()
    
    # Clear existing tiles
    import shutil
    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    total_tiles = 0
    for i, date_str in enumerate(dates_to_process):
        print(f"[{i+1}/{len(dates_to_process)}] Processing {date_str}...")
        
        # Find the time index for this date
        time_idx = dates.index(date_str)
        
        # Extract values for this date
        values = ds.dis24.isel(valid_time=time_idx).values
        
        # Check data
        valid_count = np.count_nonzero(np.isfinite(values) & (values > 0))
        print(f"  Valid pixels: {valid_count}")
        
        # Generate tiles
        tile_count = generate_tiles_for_date(date_str, values, lats, lons, adm0_geom, color_stops)
        total_tiles += tile_count
        print(f"  Generated {tile_count} tiles")
        print()
    
    ds.close()
    
    print("=" * 60)
    print(f"Complete! Generated {total_tiles} tiles")
    print(f"Output: {OUTPUT_DIR}")
    print("=" * 60)


if __name__ == "__main__":
    main()
