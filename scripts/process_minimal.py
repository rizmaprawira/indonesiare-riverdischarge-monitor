#!/usr/bin/env python3
"""
Minimal data processing - skip tiles for quick testing.
Generates: metadata, layers, points, series, rankings, grids
"""

import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
from shapely.geometry import Point, shape
from shapely.prepared import prep

try:
    import xarray as xr
except ImportError:
    print("pip install xarray netcdf4")
    exit(1)

PROJECT_ROOT = Path(__file__).parent.parent
NC_FILE = PROJECT_ROOT / "data_20-29march2026.nc"
OUTPUT_DIR = PROJECT_ROOT / "public" / "data" / "latest"
BOUNDARY_FILE = OUTPUT_DIR / "boundaries" / "provinces.geojson"

TARGET_POINTS = 600
MIN_MEAN_DISCHARGE = 10.0
MIN_PER_PROVINCE = 2

JAVA_BONUS_POINTS = 100
SULAWESI_BONUS_POINTS = 60
SUMATRA_BONUS_POINTS = 40

JAVA_PROVINCES = {
    "Banten",
    "Jakarta Special Capital Region",
    "West Java",
    "Central Java",
    "Special Region of Yogyakarta",
    "East Java",
}

SULAWESI_PROVINCES = {
    "North Sulawesi",
    "Gorontalo",
    "Central Sulawesi",
    "West Sulawesi",
    "South Sulawesi",
    "Southeast Sulawesi",
}

PRIORITY_SUMATRA_PROVINCES = {
    "North Sumatra",
    "West Sumatra",
}


def read_province_name(feature: dict) -> str:
    props = feature.get("properties", {})
    return (
        props.get("shapeName")
        or props.get("name")
        or props.get("NAME_1")
        or "Unknown"
    )


def load_province_geometries(path: Path):
    geojson = json.load(open(path, "r"))
    provinces = []
    for feature in geojson["features"]:
        name = read_province_name(feature)
        geom = shape(feature["geometry"])
        provinces.append(
            {
                "name": name,
                "geometry": geom,
                "prepared": prep(geom),
                "bounds": geom.bounds,  # minx, miny, maxx, maxy
            }
        )
    return provinces


def locate_province(lat: float, lon: float, province_geometries: list[dict]) -> str | None:
    point = Point(lon, lat)
    for province in province_geometries:
        minx, miny, maxx, maxy = province["bounds"]
        if lon < minx or lon > maxx or lat < miny or lat > maxy:
            continue
        if province["prepared"].contains(point) or province["geometry"].touches(point):
            return str(province["name"])
    return None


def add_points_with_thinning(
    pool: list[dict],
    max_add: int,
    cell_size: float,
    selected: list[dict],
    selected_cells: set[tuple[int, int]],
    selected_points: set[tuple[int, int]],
) -> int:
    occupied = {(round(point["lat"] / cell_size), round(point["lon"] / cell_size)) for point in selected}
    added = 0
    for candidate in pool:
        point_key = (candidate["lat_idx"], candidate["lon_idx"])
        if point_key in selected_points:
            continue

        cell_key = (round(candidate["lat"] / cell_size), round(candidate["lon"] / cell_size))
        if cell_key in occupied or cell_key in selected_cells:
            continue

        selected.append(candidate)
        selected_points.add(point_key)
        selected_cells.add(cell_key)
        occupied.add(cell_key)
        added += 1
        if added >= max_add:
            break

    return added


def main():
    print("=" * 60)
    print("Indonesia River Discharge Monitoring v4 - Minimal Pipeline")
    print("=" * 60)

    # Load dataset
    print(f"\nLoading dataset from {NC_FILE}")
    ds = xr.open_dataset(NC_FILE)
    
    # Extract dates
    import pandas as pd
    times = pd.to_datetime(ds.valid_time.values, unit='s')
    dates = [t.strftime("%Y-%m-%d") for t in times]
    print(f"Found {len(dates)} dates: {dates[0]} to {dates[-1]}")

    lats = ds.latitude.values
    lons = ds.longitude.values
    
    # Ensure output directories
    for subdir in ["grids", "series", "legends", "tiles"]:
        (OUTPUT_DIR / subdir).mkdir(parents=True, exist_ok=True)

    province_geometries = load_province_geometries(BOUNDARY_FILE)
    province_names = [province["name"] for province in province_geometries]
    
    # ========================
    # 1. Generate Metadata
    # ========================
    print("\n1. Generating metadata.json...")
    metadata = {
        "mode": "historical",
        "dataSource": "GloFAS Historical",
        "latestDate": dates[-1],
        "oldestDate": dates[0],
        "availableDates": dates,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "lagDays": 3,
        "bounds": {
            "north": float(lats.max()),
            "south": float(lats.min()),
            "east": float(lons.max()),
            "west": float(lons.min())
        }
    }
    with open(OUTPUT_DIR / "metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)
    print("  ✓ metadata.json")
    
    # ========================
    # 2. Generate Layers
    # ========================
    print("\n2. Generating layers.json...")
    layers = {}
    for i, date_str in enumerate(dates):
        layers[date_str] = {
            "id": f"date_{date_str}",
            "date": date_str,
            "label": pd.to_datetime(date_str).strftime("%b %d"),
            "index": i
        }
    with open(OUTPUT_DIR / "layers.json", "w") as f:
        json.dump({"layers": layers, "defaultDate": dates[-1]}, f, indent=2)
    print("  ✓ layers.json")
    
    # ========================
    # 3. Generate Grids
    # ========================
    print("\n3. Generating grid files...")
    for i, date_str in enumerate(dates):
        data = ds.dis24.isel(valid_time=i).values
        
        # Keep native 0.05° resolution (same as source NC and v3 behavior)
        step = 1
        grid_data = {
            "lats": [round(float(lat), 4) for lat in lats[::step]],
            "lons": [round(float(lon), 4) for lon in lons[::step]],
            "values": []
        }
        for row in data[::step]:
            row_vals = [None if np.isnan(v) else round(float(v), 2) for v in row[::step]]
            grid_data["values"].append(row_vals)
        
        with open(OUTPUT_DIR / "grids" / f"{date_str}.json", "w") as f:
            json.dump(grid_data, f)
        print(f"  ✓ grids/{date_str}.json")
    
    # ========================
    # 4. Select Monitoring Points
    # ========================
    print("\n4. Selecting monitoring points...")
    mean_discharge = ds.dis24.mean(dim="valid_time").values
    
    candidates = []
    for lat_idx, lat in enumerate(lats):
        for lon_idx, lon in enumerate(lons):
            val = mean_discharge[lat_idx, lon_idx]
            if np.isnan(val) or float(val) <= MIN_MEAN_DISCHARGE:
                continue

            province_name = locate_province(float(lat), float(lon), province_geometries)
            if province_name is None:
                continue

            candidates.append(
                {
                    "lat_idx": lat_idx,
                    "lon_idx": lon_idx,
                    "lat": float(lat),
                    "lon": float(lon),
                    "discharge": float(val),
                    "province": province_name,
                }
            )
    
    print(f"  Found {len(candidates)} candidate cells")
    
    # Sort by discharge descending
    candidates.sort(key=lambda x: x["discharge"], reverse=True)
    
    # Select points ensuring all provinces
    selected = []
    provinces_covered = set()
    cell_size = 0.25
    occupied_cells = set()
    selected_points = set()
    
    # First pass: ensure each province has at least MIN_PER_PROVINCE points
    for prov in province_names:
        prov_candidates = [c for c in candidates if c["province"] == prov]
        added = 0
        for c in prov_candidates:
            cell_key = (round(c["lat"] / cell_size), round(c["lon"] / cell_size))
            point_key = (c["lat_idx"], c["lon_idx"])
            if cell_key not in occupied_cells and point_key not in selected_points:
                selected.append(c)
                occupied_cells.add(cell_key)
                selected_points.add(point_key)
                provinces_covered.add(prov)
                added += 1
                if added >= MIN_PER_PROVINCE:
                    break
    
    print(f"  After province coverage: {len(selected)} points, {len(provinces_covered)} provinces")

    # Priority boosts requested by user
    java_pool = [c for c in candidates if c["province"] in JAVA_PROVINCES]
    sulawesi_pool = [c for c in candidates if c["province"] in SULAWESI_PROVINCES]
    sumatra_pool = [c for c in candidates if c["province"] in PRIORITY_SUMATRA_PROVINCES]

    added_java = add_points_with_thinning(
        java_pool,
        JAVA_BONUS_POINTS,
        0.12,
        selected,
        occupied_cells,
        selected_points,
    )
    print(f"  Added Java bonus points: {added_java}")

    added_sulawesi = add_points_with_thinning(
        sulawesi_pool,
        SULAWESI_BONUS_POINTS,
        0.16,
        selected,
        occupied_cells,
        selected_points,
    )
    print(f"  Added Sulawesi bonus points: {added_sulawesi}")

    added_sumatra = add_points_with_thinning(
        sumatra_pool,
        SUMATRA_BONUS_POINTS,
        0.16,
        selected,
        occupied_cells,
        selected_points,
    )
    print(f"  Added North/West Sumatra bonus points: {added_sumatra}")

    # Final pass: fill to target
    for c in candidates:
        if len(selected) >= TARGET_POINTS:
            break
        cell_key = (round(c["lat"] / cell_size), round(c["lon"] / cell_size))
        point_key = (c["lat_idx"], c["lon_idx"])
        if cell_key not in occupied_cells and point_key not in selected_points:
            selected.append(c)
            occupied_cells.add(cell_key)
            selected_points.add(point_key)
            provinces_covered.add(c["province"])

    print(f"  Final: {len(selected)} points, {len(provinces_covered)} provinces")
    
    # ========================
    # 5. Generate Points GeoJSON (with values per date)
    # ========================
    print("\n5. Generating points.geojson...")
    features = []
    for idx, pt in enumerate(selected):
        # Get discharge values for each date
        values = {}
        for t, date_str in enumerate(dates):
            val = ds.dis24.isel(valid_time=t).values[pt["lat_idx"], pt["lon_idx"]]
            values[date_str] = round(float(val), 2) if not np.isnan(val) else None
        
        features.append({
            "type": "Feature",
            "properties": {
                "id": f"pt_{idx:04d}",
                "province": pt["province"],
                "label": pt["province"],
                "meanDischarge": round(pt["discharge"], 2),
                "values": values
            },
            "geometry": {
                "type": "Point",
                "coordinates": [pt["lon"], pt["lat"]]
            }
        })
    
    geojson = {
        "type": "FeatureCollection",
        "features": features
    }
    with open(OUTPUT_DIR / "points.geojson", "w") as f:
        json.dump(geojson, f)
    print(f"  ✓ points.geojson ({len(features)} points)")
    
    # ========================
    # 6. Generate Time Series
    # ========================
    print("\n6. Generating time series...")
    series_dir = OUTPUT_DIR / "series"
    
    for idx, pt in enumerate(selected):
        point_id = f"pt_{idx:04d}"
        values = []
        for t in range(len(dates)):
            val = ds.dis24.isel(valid_time=t).values[pt["lat_idx"], pt["lon_idx"]]
            values.append(round(float(val), 2) if not np.isnan(val) else None)
        
        series_data = {
            "pointId": point_id,
            "province": pt["province"],
            "coordinates": [pt["lon"], pt["lat"]],
            "dates": dates,
            "values": values,
            "summary": {
                "min": min([v for v in values if v is not None], default=0),
                "max": max([v for v in values if v is not None], default=0),
                "mean": round(np.nanmean([v for v in values if v is not None]), 2) if any(v is not None for v in values) else 0
            }
        }
        
        with open(series_dir / f"{point_id}.json", "w") as f:
            json.dump(series_data, f)
    
    print(f"  ✓ Generated {len(selected)} series files")
    
    # ========================
    # 7. Generate Rankings
    # ========================
    print("\n7. Generating rankings.json...")
    
    # Get latest date discharge values
    latest_idx = len(dates) - 1
    rankings_data = []
    for idx, pt in enumerate(selected):
        val = ds.dis24.isel(valid_time=latest_idx).values[pt["lat_idx"], pt["lon_idx"]]
        if not np.isnan(val):
            rankings_data.append({
                "pointId": f"pt_{idx:04d}",
                "province": pt["province"],
                "discharge": round(float(val), 2),
                "coordinates": [pt["lon"], pt["lat"]]
            })
    
    rankings_data.sort(key=lambda x: x["discharge"], reverse=True)
    
    rankings = {
        "date": dates[-1],
        "items": rankings_data[:50]  # Top 50
    }
    with open(OUTPUT_DIR / "rankings.json", "w") as f:
        json.dump(rankings, f, indent=2)
    print(f"  ✓ rankings.json (top 50)")
    
    # ========================
    # 8. Generate Legends (matching v3 YlGnBu color scheme)
    # ========================
    print("\n8. Generating legend files...")
    
    legend_stops = [
        {"value": 1, "color": "#F6F9D6", "label": "1"},
        {"value": 5, "color": "#E5F2C8", "label": "5"},
        {"value": 10, "color": "#D5EAB5", "label": "10"},
        {"value": 25, "color": "#A8D6A7", "label": "25"},
        {"value": 50, "color": "#6FB7AE", "label": "50"},
        {"value": 100, "color": "#3E91B5", "label": "100"},
        {"value": 200, "color": "#327FAF", "label": "200"},
        {"value": 300, "color": "#2A6EAA", "label": "300"},
        {"value": 400, "color": "#2461A1", "label": "400"},
        {"value": 500, "color": "#215398", "label": "500"},
        {"value": 1000, "color": "#1D3E7B", "label": ">1000"}
    ]
    
    for date_str in dates:
        legend = {
            "title": "River Discharge (m³/s)",
            "date": date_str,
            "stops": legend_stops
        }
        with open(OUTPUT_DIR / "legends" / f"{date_str}.json", "w") as f:
            json.dump(legend, f, indent=2)
    
    print(f"  ✓ Generated {len(dates)} legend files")
    
    print("\n" + "=" * 60)
    print("Pipeline complete!")
    print(f"Output: {OUTPUT_DIR}")
    print("=" * 60)
    print("\nNote: Tile generation skipped for speed. Use process_historical.py for full tiles.")


if __name__ == "__main__":
    main()
