#!/usr/bin/env python3
"""
Minimal data processing - skip tiles for quick testing.
Generates: metadata, layers, points, series, rankings, grids
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path
import numpy as np

try:
    import xarray as xr
except ImportError:
    print("pip install xarray netcdf4")
    exit(1)

PROJECT_ROOT = Path(__file__).parent.parent
NC_FILE = PROJECT_ROOT / "data_19-28march2026.nc"
OUTPUT_DIR = PROJECT_ROOT / "public" / "data" / "latest"

# Province bounding boxes (simplified)
PROVINCES = {
    "Aceh": {"lat_min": 2.0, "lat_max": 6.0, "lon_min": 95.0, "lon_max": 98.5},
    "Sumatera Utara": {"lat_min": 1.0, "lat_max": 4.5, "lon_min": 97.0, "lon_max": 100.5},
    "Sumatera Barat": {"lat_min": -3.5, "lat_max": 1.5, "lon_min": 98.5, "lon_max": 102.0},
    "Riau": {"lat_min": -1.0, "lat_max": 2.5, "lon_min": 100.0, "lon_max": 105.0},
    "Jambi": {"lat_min": -3.0, "lat_max": 0.0, "lon_min": 101.0, "lon_max": 105.0},
    "Sumatera Selatan": {"lat_min": -5.0, "lat_max": -1.5, "lon_min": 102.0, "lon_max": 106.5},
    "Bengkulu": {"lat_min": -5.5, "lat_max": -2.0, "lon_min": 101.0, "lon_max": 103.5},
    "Lampung": {"lat_min": -6.5, "lat_max": -3.5, "lon_min": 103.5, "lon_max": 106.5},
    "Kepulauan Bangka Belitung": {"lat_min": -4.0, "lat_max": -1.0, "lon_min": 105.0, "lon_max": 109.0},
    "Kepulauan Riau": {"lat_min": -1.0, "lat_max": 5.0, "lon_min": 103.0, "lon_max": 110.0},
    "DKI Jakarta": {"lat_min": -6.4, "lat_max": -5.9, "lon_min": 106.6, "lon_max": 107.1},
    "Jawa Barat": {"lat_min": -7.8, "lat_max": -5.9, "lon_min": 106.3, "lon_max": 108.9},
    "Jawa Tengah": {"lat_min": -8.2, "lat_max": -5.9, "lon_min": 108.8, "lon_max": 111.5},
    "DI Yogyakarta": {"lat_min": -8.2, "lat_max": -7.4, "lon_min": 110.0, "lon_max": 110.7},
    "Jawa Timur": {"lat_min": -8.8, "lat_max": -5.8, "lon_min": 111.0, "lon_max": 114.7},
    "Banten": {"lat_min": -7.2, "lat_max": -5.8, "lon_min": 105.0, "lon_max": 106.7},
    "Bali": {"lat_min": -8.9, "lat_max": -8.0, "lon_min": 114.4, "lon_max": 115.8},
    "Nusa Tenggara Barat": {"lat_min": -9.2, "lat_max": -8.0, "lon_min": 115.5, "lon_max": 119.5},
    "Nusa Tenggara Timur": {"lat_min": -11.0, "lat_max": -8.0, "lon_min": 118.0, "lon_max": 125.5},
    "Kalimantan Barat": {"lat_min": -3.5, "lat_max": 2.5, "lon_min": 108.0, "lon_max": 115.0},
    "Kalimantan Tengah": {"lat_min": -4.0, "lat_max": 0.5, "lon_min": 110.5, "lon_max": 116.5},
    "Kalimantan Selatan": {"lat_min": -5.0, "lat_max": -1.5, "lon_min": 114.0, "lon_max": 117.0},
    "Kalimantan Timur": {"lat_min": -2.5, "lat_max": 4.5, "lon_min": 113.5, "lon_max": 119.5},
    "Kalimantan Utara": {"lat_min": 1.5, "lat_max": 4.5, "lon_min": 115.0, "lon_max": 118.5},
    "Sulawesi Utara": {"lat_min": -0.5, "lat_max": 4.5, "lon_min": 122.5, "lon_max": 127.5},
    "Sulawesi Tengah": {"lat_min": -3.5, "lat_max": 1.0, "lon_min": 119.5, "lon_max": 124.5},
    "Sulawesi Selatan": {"lat_min": -7.5, "lat_max": -1.5, "lon_min": 118.5, "lon_max": 121.5},
    "Sulawesi Tenggara": {"lat_min": -6.5, "lat_max": -2.5, "lon_min": 120.5, "lon_max": 124.5},
    "Gorontalo": {"lat_min": -0.5, "lat_max": 1.5, "lon_min": 121.5, "lon_max": 123.5},
    "Sulawesi Barat": {"lat_min": -3.5, "lat_max": 0.0, "lon_min": 118.5, "lon_max": 120.0},
    "Maluku": {"lat_min": -9.0, "lat_max": 1.5, "lon_min": 124.0, "lon_max": 135.5},
    "Maluku Utara": {"lat_min": -2.0, "lat_max": 3.5, "lon_min": 124.0, "lon_max": 129.5},
    "Papua Barat": {"lat_min": -5.0, "lat_max": 0.5, "lon_min": 129.0, "lon_max": 135.5},
    "Papua": {"lat_min": -9.5, "lat_max": -0.5, "lon_min": 134.0, "lon_max": 141.5},
    "Papua Selatan": {"lat_min": -9.0, "lat_max": -5.0, "lon_min": 136.0, "lon_max": 141.0},
    "Papua Tengah": {"lat_min": -6.0, "lat_max": -2.5, "lon_min": 136.0, "lon_max": 140.5},
    "Papua Pegunungan": {"lat_min": -5.5, "lat_max": -3.0, "lon_min": 137.0, "lon_max": 141.5},
    "Papua Barat Daya": {"lat_min": -4.5, "lat_max": -0.5, "lon_min": 129.5, "lon_max": 133.5},
}


def get_province(lat: float, lon: float) -> str:
    """Get province name for a lat/lon coordinate."""
    for name, bounds in PROVINCES.items():
        if (bounds["lat_min"] <= lat <= bounds["lat_max"] and
            bounds["lon_min"] <= lon <= bounds["lon_max"]):
            return name
    return "Indonesia"


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
    layers = []
    for i, date_str in enumerate(dates):
        layers.append({
            "id": f"date_{date_str}",
            "date": date_str,
            "label": pd.to_datetime(date_str).strftime("%b %d"),
            "index": i
        })
    with open(OUTPUT_DIR / "layers.json", "w") as f:
        json.dump({"layers": layers}, f, indent=2)
    print("  ✓ layers.json")
    
    # ========================
    # 3. Generate Grids
    # ========================
    print("\n3. Generating grid files...")
    for i, date_str in enumerate(dates):
        data = ds.dis24.isel(valid_time=i).values
        
        # Downsample for smaller files (every 2nd cell)
        step = 2
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
    print("\n4. Selecting 500 monitoring points...")
    mean_discharge = ds.dis24.mean(dim="valid_time").values
    
    candidates = []
    for lat_idx, lat in enumerate(lats):
        for lon_idx, lon in enumerate(lons):
            val = mean_discharge[lat_idx, lon_idx]
            if not np.isnan(val) and val > 30:  # Min threshold
                candidates.append({
                    "lat_idx": lat_idx,
                    "lon_idx": lon_idx,
                    "lat": float(lat),
                    "lon": float(lon),
                    "discharge": float(val),
                    "province": get_province(float(lat), float(lon))
                })
    
    print(f"  Found {len(candidates)} candidate cells")
    
    # Sort by discharge descending
    candidates.sort(key=lambda x: x["discharge"], reverse=True)
    
    # Select points ensuring all provinces
    selected = []
    provinces_covered = set()
    cell_size = 0.3
    occupied_cells = set()
    
    # First pass: ensure each province has at least 2 points
    for prov in PROVINCES.keys():
        prov_candidates = [c for c in candidates if c["province"] == prov]
        added = 0
        for c in prov_candidates:
            cell_key = (round(c["lat"] / cell_size), round(c["lon"] / cell_size))
            if cell_key not in occupied_cells:
                selected.append(c)
                occupied_cells.add(cell_key)
                provinces_covered.add(prov)
                added += 1
                if added >= 2:
                    break
    
    print(f"  After province coverage: {len(selected)} points, {len(provinces_covered)} provinces")
    
    # Second pass: fill to 500 with spatial thinning
    for c in candidates:
        if len(selected) >= 500:
            break
        cell_key = (round(c["lat"] / cell_size), round(c["lon"] / cell_size))
        if cell_key not in occupied_cells:
            selected.append(c)
            occupied_cells.add(cell_key)
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
        {"value": 10, "color": "#D5EAB5", "label": "10"},
        {"value": 25, "color": "#A8D6A7", "label": "25"},
        {"value": 50, "color": "#6FB7AE", "label": "50"},
        {"value": 100, "color": "#3E91B5", "label": "100"},
        {"value": 250, "color": "#2A6EAA", "label": "250"},
        {"value": 500, "color": "#215398", "label": "500"},
        {"value": 1000, "color": "#1D3E7B", "label": "1000"},
        {"value": 2500, "color": "#582F7A", "label": "2500"},
        {"value": 5000, "color": "#8B2D63", "label": "5000"},
        {"value": 10000, "color": "#B7373B", "label": ">10000"}
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
