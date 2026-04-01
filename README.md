# Indonesia River Discharge Monitor

A real-time interactive dashboard for monitoring river discharge across Indonesia using satellite-based hydrological data from the Copernicus Climate Data Store.

🌍 **Live Dashboard**: [IndonesiaRe River Discharge Monitor](https://indonesiare.github.io/indonesiare-riverdischarge-monitor/)

---

## What is This?

The Indonesia River Discharge Monitor provides **daily updates** on water flow (discharge) across Indonesia's major river systems. This data is critical for:

- **Disaster Risk Assessment**: Early identification of flood-prone areas during high discharge periods
- **Water Resource Management**: Planning irrigation, hydropower, and water supply operations
- **Climate Monitoring**: Tracking how precipitation patterns affect river systems
- **Insurance & Reinsurance**: Understanding hydro-hazard exposure for river basins

The dashboard displays data from the **Copernicus Global Flood Awareness System (GloFAS)**, a European Space Agency initiative that provides global hydrological forecasts and historical data.

---

## How to Use the Dashboard

### **Map View**
- **Interactive heatmap** shows discharge intensity across Indonesia (yellow = low flow, blue = high flow)
- **Zoom in/out** to see specific regions at different detail levels
- **Hover over the map** to see exact discharge values at any location
- **Click provinces** to see administrative boundaries

### **River Stations**
- **600 key river monitoring points** are marked with blue dots
- **Click any dot** to view detailed information:
  - River name and location
  - Current discharge (m³/s)
  - 10-day historical trend chart
  - Province and water basin information

### **Summary Panel**
- **Top 50 rivers** ranked by current discharge
- Automatic updates when you change the date

### **Date Selection**
- View historical data by selecting different dates
- Data updated daily with latest GloFAS discharge estimates

### **Opacity Control**
- Adjust the transparency of the discharge heatmap overlay
- Useful for seeing underlying map features

---

## Data Source

### GloFAS (Global Flood Awareness System)
- **Provider**: Copernicus Emergency Management Service - Early Warning Data Store
- **Data Type**: Hydrological model output LISFLOOD (not direct measurements)
- **Resolution**: ~0.05 km grid cells across Indonesia
- **Temporal Coverage**: Daily mean river discharge estimates
- **Variable**: `dis24` - Mean river discharge over 24-hour period (m³/s)

### Spatial Coverage
- **Region**: Full Indonesian archipelago (94°E - 145°E, 12°S - 8°N)
- **600 Sampled Points**: Strategically selected to represent major river systems

### Data Updates (ON PROGRESS)
- New data is added approximately **daily** with time lag of 2-4 days
- Historical archive available for trend analysis
- All dates shown in UTC timezone

---


## Technical Details

### Technology Stack
- **Frontend**: React 18 + TypeScript + Leaflet (interactive maps)
- **Data Visualization**: ECharts (time-series charts)
- **Build Tool**: Vite (fast development builds)
- **Hosting**: GitHub Pages (static deployment)
- **Data Format**: Geospatial PNG tiles + JSON metadata

### Architecture
1. **Data Processing Layer**: Python scripts convert daily NetCDF data into web-ready tiles and metadata
2. **Static Data Layer**: Pre-computed tiles, points, rankings, and time-series stored as JSON
3. **Frontend Layer**: React app renders interactive map, panels, and controls
4. **Deployment**: Automated via GitHub Pages

### Performance Features
- **Lazy Loading**: Data loads only when needed
- **Client-Side Rendering**: All computation happens in your browser
- **No Backend API**: Purely static files (faster, no server costs) (API SUPPORT ARE ON PROGRESS)
- **Tile Caching**: Browser caches map tiles for fast navigation

---

## Limitations & Disclaimers

⚠️ **Important**: This dashboard shows **model outputs, not direct measurements**.

### Known Limitations
1. **Model Uncertainty**: GloFAS predictions have inherent modeling uncertainty, especially in extreme events
2. **Resolution Limits**: 0.05 km grid may smooth local variations
3. **Data Lag**: Typically 2-4 days behind real-time
4. **Coastal Sensitivity**: Model performance degrades in coastal areas with complex hydrology
5. **Monsoon Bias**: Seasonal prediction skill varies with monsoon patterns

### Not Suitable For
- Emergency flood response (use official government flood alerts instead)
- Legal liability claims without independent verification
- Precise point-scale predictions for individual locations
- Sub-daily discharge variations

### Recommended Use
- Strategic risk assessment and planning
- Long-term trend analysis
- Historical reference data
- Validation against ground observations
- Situational awareness only

---

## Frequently Asked Questions

### Q: How often is the data updated?
**A**: New discharge estimates are planned to be added approximately daily, though it is still in progress. The exact update schedule depends on GloFAS data availability.

### Q: Why does my location show no data?
**A**: Some areas (particularly coastal zones and small islands) may have sparse GloFAS data due to model resolution and data availability.

### Q: Can I download the raw data?
**A**: Yes! All underlying data is derived from Copernicus GloFAS. Visit https://ewds.climate.copernicus.eu/ to access the full dataset.

### Q: How is the 600-point selection made?
**A**: Selected at main river, at least 2 rivers per province are included.

### Q: What time zone is used?
**A**: All times are in UTC (Coordinated Universal Time).

### Q: Can I use this for insurance/reinsurance?
**A**: This is reference data only. Proper risk assessment requires validated ground data, expert analysis, and may need independent model runs.

---

## Getting Help

### Report Issues
- **GitHub Issues**: https://github.com/indonesiare/indonesiare-riverdischarge-monitor/issues
- Include date, location, and what you expected to see

### Contact
- Rizma: 12822029@mahasiswa.itb.ac.id
  
---

## License & Attribution

### Data Attribution
- **GloFAS Data**: © Copernicus Emergency Monitoring Service
- **Base Map**: © OpenStreetMap contributors
- **Province Boundaries**: Indonesian government spatial data

### Terms of Use
This dashboard is provided for informational purposes and still in developing. While we strive for accuracy, we make no warranties regarding completeness, accuracy, or fitness for specific purposes. Users assume all responsibility for decisions made based on this data.

---

**Last Updated**: April 2026  
**Version**: 4.0
