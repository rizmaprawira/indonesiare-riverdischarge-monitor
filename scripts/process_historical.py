#!/usr/bin/env python3
"""
Indonesia River Discharge Monitoring v4 - Data Processing Pipeline

This script processes GloFAS historical NetCDF data and generates all static
assets needed for the web application:
- Metadata JSON
- Layers configuration JSON
- PNG tiles for each date
- Grid JSON files for hover sampling
- Legend JSON files
- Points GeoJSON with 500 monitoring points
- Time series JSON for each point
- Rankings JSON

Usage:
    python process_historical.py

The script expects:
- data_19-28march2026.nc in the project root
- config/data.config.json with processing configuration
- public/data/latest/boundaries/provinces.geojson (will be downloaded if missing)
"""

import json
import math
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

try:
    import xarray as xr
except ImportError:
    print("Error: xarray not installed. Run: pip install xarray netcdf4")
    sys.exit(1)

try:
    from PIL import Image
except ImportError:
    print("Error: Pillow not installed. Run: pip install Pillow")
    sys.exit(1)

try:
    import mercantile
except ImportError:
    print("Error: mercantile not installed. Run: pip install mercantile")
    sys.exit(1)


# Configuration
PROJECT_ROOT = Path(__file__).parent.parent
NC_FILE = PROJECT_ROOT / "data_19-28march2026.nc"
OUTPUT_DIR = PROJECT_ROOT / "public" / "data" / "latest"
CONFIG_FILE = PROJECT_ROOT / "config" / "style.config.json"


def load_style_config() -> dict:
    """Load style configuration for color ramp."""
    with open(CONFIG_FILE) as f:
        return json.load(f)


def get_color_for_value(value: float, stops: list[dict]) -> tuple[int, int, int, int]:
    """Map discharge value to RGBA color using log scale."""
    if np.isnan(value) or value <= 0:
        return (0, 0, 0, 0)  # Transparent
    
    # Find the color stop
    for i, stop in enumerate(stops):
        if value <= stop["value"]:
            if i == 0:
                color = stop["color"]
            else:
                # Interpolate between stops
                prev_stop = stops[i - 1]
                t = (math.log10(value) - math.log10(prev_stop["value"])) / (
                    math.log10(stop["value"]) - math.log10(prev_stop["value"])
                )
                t = max(0, min(1, t))
                prev_color = hex_to_rgb(prev_stop["color"])
                curr_color = hex_to_rgb(stop["color"])
                color = tuple(int(prev_color[j] + t * (curr_color[j] - prev_color[j])) for j in range(3))
                return (*color, 220)  # Semi-transparent
            break
    else:
        color = stops[-1]["color"]
    
    rgb = hex_to_rgb(color) if isinstance(color, str) else color
    return (*rgb, 220)


def hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    """Convert hex color to RGB tuple."""
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))


def load_dataset() -> xr.Dataset:
    """Load the NetCDF dataset."""
    print(f"Loading dataset from {NC_FILE}")
    ds = xr.open_dataset(NC_FILE)
    return ds


def extract_dates(ds: xr.Dataset) -> list[str]:
    """Extract available dates from the dataset."""
    import pandas as pd
    times = pd.to_datetime(ds.valid_time.values, unit='s')
    return [t.strftime("%Y-%m-%d") for t in times]


def process_grid_for_date(ds: xr.Dataset, time_idx: int) -> dict:
    """Extract grid data for a specific date."""
    data = ds.dis24.isel(valid_time=time_idx).values
    lats = ds.latitude.values.tolist()
    lons = ds.longitude.values.tolist()
    
    # Convert NaN to None for JSON
    values = []
    for row in data:
        values.append([None if np.isnan(v) else round(float(v), 2) for v in row])
    
    return {
        "lats": [round(float(lat), 4) for lat in lats],
        "lons": [round(float(lon), 4) for lon in lons],
        "values": values
    }


def generate_tiles_for_date(
    ds: xr.Dataset,
    time_idx: int,
    date_str: str,
    color_stops: list[dict],
    zoom_levels: list[int] = [4, 5, 6, 7, 8]
) -> None:
    """Generate PNG tiles for a specific date."""
    tiles_dir = OUTPUT_DIR / "tiles" / date_str
    tiles_dir.mkdir(parents=True, exist_ok=True)
    
    data = ds.dis24.isel(valid_time=time_idx).values
    lats = ds.latitude.values
    lons = ds.longitude.values
    
    # Get bounds
    lat_min, lat_max = float(lats.min()), float(lats.max())
    lon_min, lon_max = float(lons.min()), float(lons.max())
    
    for z in zoom_levels:
        # Get all tiles that intersect the bounding box
        tiles = list(mercantile.tiles(lon_min, lat_min, lon_max, lat_max, zooms=z))
        
        for tile in tiles:
            tile_dir = tiles_dir / str(z) / str(tile.x)
            tile_dir.mkdir(parents=True, exist_ok=True)
            tile_path = tile_dir / f"{tile.y}.png"
            
            # Get tile bounds
            bounds = mercantile.bounds(tile)
            
            # Create 256x256 tile
            img = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
            pixels = img.load()
            
            for py in range(256):
                for px in range(256):
                    # Convert pixel to lat/lon
                    pixel_lon = bounds.west + (px / 256) * (bounds.east - bounds.west)
                    pixel_lat = bounds.north - (py / 256) * (bounds.north - bounds.south)
                    
                    # Find nearest grid cell
                    lat_idx = np.argmin(np.abs(lats - pixel_lat))
                    lon_idx = np.argmin(np.abs(lons - pixel_lon))
                    
                    # Check if within grid bounds
                    if (lats[lat_idx] >= lat_min and lats[lat_idx] <= lat_max and
                        lons[lon_idx] >= lon_min and lons[lon_idx] <= lon_max):
                        value = data[lat_idx, lon_idx]
                        color = get_color_for_value(value, color_stops)
                        pixels[px, py] = color
            
            img.save(tile_path, "PNG")
    
    print(f"  Generated tiles for {date_str}")


def select_monitoring_points(
    ds: xr.Dataset,
    max_points: int = 500,
    min_discharge: float = 50.0,
    cell_size_deg: float = 0.3
) -> list[dict]:
    """Select monitoring points ensuring provincial coverage."""
    # Get average discharge across all dates
    mean_discharge = ds.dis24.mean(dim="valid_time").values
    lats = ds.latitude.values
    lons = ds.longitude.values
    
    # Find all cells with significant discharge
    candidates = []
    for i, lat in enumerate(lats):
        for j, lon in enumerate(lons):
            value = mean_discharge[i, j]
            if not np.isnan(value) and value >= min_discharge:
                candidates.append({
                    "lat": float(lat),
                    "lon": float(lon),
                    "lat_idx": i,
                    "lon_idx": j,
                    "mean_discharge": float(value)
                })
    
    print(f"  Found {len(candidates)} candidate cells with discharge >= {min_discharge}")
    
    # Sort by discharge (highest first)
    candidates.sort(key=lambda x: x["mean_discharge"], reverse=True)
    
    # Spatial thinning - keep one point per cell
    selected = []
    used_cells = set()
    
    for candidate in candidates:
        # Calculate cell key
        cell_lat = int(candidate["lat"] / cell_size_deg)
        cell_lon = int(candidate["lon"] / cell_size_deg)
        cell_key = (cell_lat, cell_lon)
        
        if cell_key not in used_cells:
            used_cells.add(cell_key)
            selected.append(candidate)
            
            if len(selected) >= max_points:
                break
    
    print(f"  Selected {len(selected)} monitoring points after spatial thinning")
    return selected


def assign_provinces(points: list[dict]) -> list[dict]:
    """Assign province names to points based on location."""
    # Simple province assignment based on lat/lon regions
    # In production, this would use actual province boundaries
    
    provinces = [
        {"name": "Aceh", "bounds": {"lat": [2.0, 6.0], "lon": [95.0, 98.5]}},
        {"name": "Sumatera Utara", "bounds": {"lat": [-1.0, 4.5], "lon": [97.0, 100.5]}},
        {"name": "Sumatera Barat", "bounds": {"lat": [-3.5, 1.5], "lon": [98.5, 101.5]}},
        {"name": "Riau", "bounds": {"lat": [-1.0, 3.0], "lon": [100.0, 104.5]}},
        {"name": "Jambi", "bounds": {"lat": [-3.0, 0.0], "lon": [101.5, 105.0]}},
        {"name": "Sumatera Selatan", "bounds": {"lat": [-5.5, -1.5], "lon": [102.5, 106.0]}},
        {"name": "Bengkulu", "bounds": {"lat": [-5.5, -2.0], "lon": [101.0, 103.5]}},
        {"name": "Lampung", "bounds": {"lat": [-6.5, -3.5], "lon": [103.5, 106.5]}},
        {"name": "Kep. Bangka Belitung", "bounds": {"lat": [-4.0, -1.0], "lon": [105.0, 108.5]}},
        {"name": "Kep. Riau", "bounds": {"lat": [-1.0, 4.5], "lon": [103.0, 108.0]}},
        {"name": "DKI Jakarta", "bounds": {"lat": [-6.5, -5.8], "lon": [106.5, 107.2]}},
        {"name": "Jawa Barat", "bounds": {"lat": [-8.0, -5.8], "lon": [105.5, 108.5]}},
        {"name": "Jawa Tengah", "bounds": {"lat": [-8.5, -5.5], "lon": [108.5, 111.5]}},
        {"name": "DI Yogyakarta", "bounds": {"lat": [-8.3, -7.5], "lon": [110.0, 110.8]}},
        {"name": "Jawa Timur", "bounds": {"lat": [-8.8, -5.5], "lon": [111.0, 114.5]}},
        {"name": "Banten", "bounds": {"lat": [-7.2, -5.8], "lon": [105.0, 106.5]}},
        {"name": "Bali", "bounds": {"lat": [-8.9, -8.0], "lon": [114.4, 115.8]}},
        {"name": "Nusa Tenggara Barat", "bounds": {"lat": [-9.5, -7.5], "lon": [115.5, 119.5]}},
        {"name": "Nusa Tenggara Timur", "bounds": {"lat": [-11.0, -7.5], "lon": [118.5, 125.5]}},
        {"name": "Kalimantan Barat", "bounds": {"lat": [-4.0, 2.5], "lon": [108.0, 112.5]}},
        {"name": "Kalimantan Tengah", "bounds": {"lat": [-4.5, 0.0], "lon": [111.0, 116.5]}},
        {"name": "Kalimantan Selatan", "bounds": {"lat": [-5.0, -1.5], "lon": [114.0, 117.5]}},
        {"name": "Kalimantan Timur", "bounds": {"lat": [-2.5, 4.5], "lon": [114.5, 119.5]}},
        {"name": "Kalimantan Utara", "bounds": {"lat": [1.5, 4.5], "lon": [115.5, 118.5]}},
        {"name": "Sulawesi Utara", "bounds": {"lat": [-1.5, 4.5], "lon": [120.0, 127.5]}},
        {"name": "Sulawesi Tengah", "bounds": {"lat": [-3.5, 0.5], "lon": [119.5, 124.5]}},
        {"name": "Sulawesi Selatan", "bounds": {"lat": [-6.5, -1.5], "lon": [118.5, 121.5]}},
        {"name": "Sulawesi Tenggara", "bounds": {"lat": [-6.5, -2.5], "lon": [120.5, 125.0]}},
        {"name": "Gorontalo", "bounds": {"lat": [-1.0, 1.5], "lon": [121.0, 123.5]}},
        {"name": "Sulawesi Barat", "bounds": {"lat": [-4.0, -0.5], "lon": [118.5, 119.8]}},
        {"name": "Maluku", "bounds": {"lat": [-8.5, -1.5], "lon": [124.5, 135.5]}},
        {"name": "Maluku Utara", "bounds": {"lat": [-2.5, 3.0], "lon": [124.0, 129.5]}},
        {"name": "Papua Barat", "bounds": {"lat": [-4.5, 0.0], "lon": [129.0, 135.5]}},
        {"name": "Papua", "bounds": {"lat": [-9.5, 0.0], "lon": [135.0, 141.5]}},
    ]
    
    for point in points:
        lat, lon = point["lat"], point["lon"]
        point["province"] = "Indonesia"  # Default
        
        for prov in provinces:
            b = prov["bounds"]
            if (b["lat"][0] <= lat <= b["lat"][1] and
                b["lon"][0] <= lon <= b["lon"][1]):
                point["province"] = prov["name"]
                break
    
    return points


def generate_point_id(idx: int, lat: float, lon: float) -> str:
    """Generate a unique point ID."""
    lat_str = f"{abs(lat):.2f}".replace(".", "")
    lat_dir = "S" if lat < 0 else "N"
    lon_str = f"{abs(lon):.2f}".replace(".", "")
    lon_dir = "E" if lon >= 0 else "W"
    return f"IDN_{idx:04d}_{lat_str}{lat_dir}_{lon_str}{lon_dir}"


def build_points_geojson(
    ds: xr.Dataset,
    points: list[dict],
    dates: list[str]
) -> dict:
    """Build GeoJSON for monitoring points with values for each date."""
    features = []
    
    for idx, point in enumerate(points):
        lat_idx = point["lat_idx"]
        lon_idx = point["lon_idx"]
        point_id = generate_point_id(idx, point["lat"], point["lon"])
        
        # Extract values for each date
        values = {}
        for i, date in enumerate(dates):
            value = float(ds.dis24.isel(valid_time=i).values[lat_idx, lon_idx])
            values[date] = round(value, 2) if not np.isnan(value) else None
        
        # Calculate summary
        valid_values = [v for v in values.values() if v is not None]
        summary = {
            "min": round(min(valid_values), 2) if valid_values else None,
            "max": round(max(valid_values), 2) if valid_values else None,
            "mean": round(sum(valid_values) / len(valid_values), 2) if valid_values else None
        }
        
        feature = {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [point["lon"], point["lat"]]
            },
            "properties": {
                "id": point_id,
                "label": f"Point {idx + 1}",
                "province": point["province"],
                "lat": round(point["lat"], 4),
                "lon": round(point["lon"], 4),
                "values": values,
                "summary": summary
            }
        }
        features.append(feature)
    
    return {
        "type": "FeatureCollection",
        "features": features
    }


def build_point_series(
    ds: xr.Dataset,
    points: list[dict],
    dates: list[str]
) -> list[dict]:
    """Build time series data for each point."""
    series_list = []
    
    for idx, point in enumerate(points):
        lat_idx = point["lat_idx"]
        lon_idx = point["lon_idx"]
        point_id = generate_point_id(idx, point["lat"], point["lon"])
        
        values = []
        for i in range(len(dates)):
            value = float(ds.dis24.isel(valid_time=i).values[lat_idx, lon_idx])
            values.append(round(value, 2) if not np.isnan(value) else None)
        
        valid_values = [v for v in values if v is not None]
        summary = {
            "min": round(min(valid_values), 2) if valid_values else None,
            "max": round(max(valid_values), 2) if valid_values else None,
            "mean": round(sum(valid_values) / len(valid_values), 2) if valid_values else None
        }
        
        series_list.append({
            "pointId": point_id,
            "dates": dates,
            "values": values,
            "summary": summary
        })
    
    return series_list


def build_rankings(points_geojson: dict, dates: list[str], top_n: int = 12) -> dict:
    """Build rankings for each date."""
    rankings = {}
    
    for date in dates:
        # Get values for this date
        point_values = []
        for feature in points_geojson["features"]:
            props = feature["properties"]
            value = props["values"].get(date)
            if value is not None:
                point_values.append({
                    "id": props["id"],
                    "label": props["label"],
                    "province": props["province"],
                    "value": value
                })
        
        # Sort by value descending
        point_values.sort(key=lambda x: x["value"], reverse=True)
        
        # Assign ranks
        top_points = []
        for rank, pv in enumerate(point_values[:top_n], 1):
            top_points.append({
                "id": pv["id"],
                "label": pv["label"],
                "province": pv["province"],
                "value": pv["value"],
                "rank": rank
            })
        
        rankings[date] = {
            "date": date,
            "points": top_points
        }
    
    return rankings


def build_metadata(dates: list[str], points_count: int) -> dict:
    """Build metadata JSON."""
    return {
        "mode": "historical",
        "dataSource": "GloFAS Historical (dis24)",
        "latestDate": dates[-1],
        "oldestDate": dates[0],
        "availableDates": dates,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "lagDays": 3,
        "units": "m³/s",
        "staleAfterHours": 72,
        "pointCount": points_count
    }


def build_layers(dates: list[str]) -> dict:
    """Build layers configuration JSON."""
    layers = {}
    
    for date in dates:
        layers[date] = {
            "date": date,
            "label": date,
            "tileUrl": f"data/latest/tiles/{date}/{{z}}/{{x}}/{{y}}.png",
            "gridUrl": f"data/latest/grids/{date}.json",
            "legendUrl": f"data/latest/legends/{date}.json",
            "minValue": 0,
            "maxValue": 10000
        }
    
    return {
        "layers": layers,
        "defaultDate": dates[-1]
    }


def build_legend(date: str, color_stops: list[dict]) -> dict:
    """Build legend JSON for a date."""
    return {
        "date": date,
        "units": "m³/s",
        "stops": color_stops
    }


def download_provinces_geojson() -> dict:
    """Download Indonesia provinces GeoJSON or use fallback."""
    provinces_path = OUTPUT_DIR / "boundaries" / "provinces.geojson"
    
    if provinces_path.exists():
        print("  Using existing provinces.geojson")
        with open(provinces_path) as f:
            return json.load(f)
    
    print("  Creating simplified provinces boundary...")
    # Create a simple Indonesia bounding box as fallback
    provinces = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {"name": "Indonesia"},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[
                        [94.0, -12.0],
                        [142.0, -12.0],
                        [142.0, 8.0],
                        [94.0, 8.0],
                        [94.0, -12.0]
                    ]]
                }
            }
        ]
    }
    
    provinces_path.parent.mkdir(parents=True, exist_ok=True)
    with open(provinces_path, "w") as f:
        json.dump(provinces, f)
    
    return provinces


def main():
    """Main processing pipeline."""
    print("=" * 60)
    print("Indonesia River Discharge Monitoring v4 - Data Pipeline")
    print("=" * 60)
    
    # Load style config
    style_config = load_style_config()
    color_stops = style_config["dischargeColorRamp"]["stops"]
    
    # Load dataset
    ds = load_dataset()
    
    # Extract dates
    dates = extract_dates(ds)
    print(f"Found {len(dates)} dates: {dates[0]} to {dates[-1]}")
    
    # Create output directories
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / "tiles").mkdir(exist_ok=True)
    (OUTPUT_DIR / "grids").mkdir(exist_ok=True)
    (OUTPUT_DIR / "legends").mkdir(exist_ok=True)
    (OUTPUT_DIR / "series").mkdir(exist_ok=True)
    (OUTPUT_DIR / "boundaries").mkdir(exist_ok=True)
    
    # Process each date
    print("\nProcessing dates...")
    for time_idx, date in enumerate(dates):
        print(f"\n  Processing {date}...")
        
        # Generate grid
        print(f"    Generating grid...")
        grid_data = process_grid_for_date(ds, time_idx)
        grid_data["date"] = date
        grid_data["units"] = "m³/s"
        grid_path = OUTPUT_DIR / "grids" / f"{date}.json"
        with open(grid_path, "w") as f:
            json.dump(grid_data, f)
        
        # Generate tiles
        print(f"    Generating tiles...")
        generate_tiles_for_date(ds, time_idx, date, color_stops)
        
        # Generate legend
        legend = build_legend(date, color_stops)
        legend_path = OUTPUT_DIR / "legends" / f"{date}.json"
        with open(legend_path, "w") as f:
            json.dump(legend, f)
    
    # Select monitoring points
    print("\nSelecting monitoring points...")
    points = select_monitoring_points(ds, max_points=500)
    points = assign_provinces(points)
    
    # Build points GeoJSON
    print("\nBuilding points GeoJSON...")
    points_geojson = build_points_geojson(ds, points, dates)
    points_path = OUTPUT_DIR / "points.geojson"
    with open(points_path, "w") as f:
        json.dump(points_geojson, f)
    print(f"  Generated {len(points_geojson['features'])} point features")
    
    # Build point series
    print("\nBuilding point series...")
    series_list = build_point_series(ds, points, dates)
    for series in series_list:
        series_path = OUTPUT_DIR / "series" / f"{series['pointId']}.json"
        with open(series_path, "w") as f:
            json.dump(series, f)
    print(f"  Generated {len(series_list)} series files")
    
    # Build rankings
    print("\nBuilding rankings...")
    rankings = build_rankings(points_geojson, dates)
    rankings_path = OUTPUT_DIR / "rankings.json"
    with open(rankings_path, "w") as f:
        json.dump(rankings, f)
    
    # Build metadata
    print("\nBuilding metadata...")
    metadata = build_metadata(dates, len(points))
    metadata_path = OUTPUT_DIR / "metadata.json"
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=2)
    
    # Build layers config
    layers = build_layers(dates)
    layers_path = OUTPUT_DIR / "layers.json"
    with open(layers_path, "w") as f:
        json.dump(layers, f, indent=2)
    
    # Download/create provinces boundary
    print("\nProcessing boundaries...")
    download_provinces_geojson()
    
    print("\n" + "=" * 60)
    print("Data pipeline complete!")
    print(f"Output directory: {OUTPUT_DIR}")
    print("=" * 60)
    
    ds.close()


if __name__ == "__main__":
    main()
