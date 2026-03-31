import { useEffect, useMemo, useRef, useState } from 'react';
import { GeoJSON, MapContainer, TileLayer, useMap } from 'react-leaflet';
import type { Map as LeafletMap, TileErrorEvent } from 'leaflet';
import L from 'leaflet';
import type {
  DateKey,
  GridData,
  HistoricalMetadata,
  LayersData,
  LegendData,
  PointsCollection,
  ProvincesCollection,
} from '../../types';
import { BASEMAPS, INDONESIA_BOUNDS, MAP_DEFAULTS } from '../../lib/constants';
import { formatDischarge } from '../../lib/format';
import { DATA_PATHS } from '../../lib/paths';
import { useLayerGrid } from '../../hooks/useLayerGrid';
import { MapControls } from './MapControls';
import { MapLegend } from './MapLegend';
import { PointsLayer } from './PointsLayer';
import styles from './MapView.module.css';

interface MapViewProps {
  metadata: HistoricalMetadata;
  layers: LayersData;
  points: PointsCollection;
  provinces: ProvincesCollection;
  activeDate: DateKey;
  opacity: number;
  selectedPointId: string | null;
  legend: LegendData | null;
  onPointSelect: (pointId: string) => void;
  onTileError: (message: string | null) => void;
  onDateChange: (date: DateKey) => void;
  onOpacityChange: (value: number) => void;
}

interface HoverSample {
  lat: number;
  lon: number;
  value: number | null;
}

function MapResetController({ mapRef }: { mapRef: React.MutableRefObject<LeafletMap | null> }) {
  const map = useMap();
  mapRef.current = map;

  useEffect(() => {
    map.fitBounds(
      [
        [INDONESIA_BOUNDS.south, INDONESIA_BOUNDS.west],
        [INDONESIA_BOUNDS.north, INDONESIA_BOUNDS.east],
      ],
      { padding: [20, 20] },
    );
  }, [map]);

  return null;
}

function SelectedPointFocus({
  point,
}: {
  point: [number, number] | null;
}) {
  const map = useMap();

  useEffect(() => {
    if (point) {
      map.panTo([point[1], point[0]], { animate: true });
    }
  }, [map, point]);

  return null;
}

function nearestIndex(values: number[], target: number): number {
  let closestIndex = 0;
  let closestDistance = Number.POSITIVE_INFINITY;
  for (let index = 0; index < values.length; index += 1) {
    const distance = Math.abs(values[index] - target);
    if (distance < closestDistance) {
      closestDistance = distance;
      closestIndex = index;
    }
  }
  return closestIndex;
}

function sampleGridValue(grid: GridData | null, latitude: number, longitude: number): HoverSample | null {
  if (!grid || grid.lats.length === 0 || grid.lons.length === 0) {
    return null;
  }

  const latIndex = nearestIndex(grid.lats, latitude);
  const lonIndex = nearestIndex(grid.lons, longitude);
  const row = grid.values[latIndex];
  const value = row ? row[lonIndex] ?? null : null;

  return {
    lat: grid.lats[latIndex],
    lon: grid.lons[lonIndex],
    value,
  };
}

export function MapView({
  metadata,
  layers,
  points,
  provinces,
  activeDate,
  opacity,
  selectedPointId,
  legend,
  onPointSelect,
  onTileError,
  onDateChange,
  onOpacityChange,
}: MapViewProps) {
  const defaultBasemap = BASEMAPS.find((candidate) => candidate.default)?.id ?? BASEMAPS[0].id;
  const [basemap, setBasemap] = useState(defaultBasemap);
  const [hoverSample, setHoverSample] = useState<HoverSample | null>(null);
  const mapRef = useRef<LeafletMap | null>(null);

  const basemapConfig = useMemo(
    () => BASEMAPS.find((candidate) => candidate.id === basemap) ?? BASEMAPS[0],
    [basemap],
  );

  const bounds = useMemo(
    () =>
      L.latLngBounds(
        [INDONESIA_BOUNDS.south, INDONESIA_BOUNDS.west],
        [INDONESIA_BOUNDS.north, INDONESIA_BOUNDS.east],
      ),
    [],
  );

  const selectedCoordinates = useMemo(() => {
    const point = points.features.find((feature) => feature.properties?.id === selectedPointId);
    const coords = point?.geometry.coordinates;
    return coords ? [coords[0], coords[1]] as [number, number] : null;
  }, [points.features, selectedPointId]);

  const layerInfo = layers.layers[activeDate];
  const { grid: layerGrid } = useLayerGrid(activeDate);

  useEffect(() => {
    setHoverSample(null);
  }, [activeDate]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map) {
      return;
    }

    function handleMouseMove(event: L.LeafletMouseEvent) {
      setHoverSample(sampleGridValue(layerGrid, event.latlng.lat, event.latlng.lng));
    }

    function handleMouseOut() {
      setHoverSample(null);
    }

    map.on('mousemove', handleMouseMove);
    map.on('mouseout', handleMouseOut);
    return () => {
      map.off('mousemove', handleMouseMove);
      map.off('mouseout', handleMouseOut);
    };
  }, [layerGrid]);

  const tileUrl = DATA_PATHS.tiles(activeDate);

  return (
    <section className={styles.mapStage}>
      <MapContainer
        center={MAP_DEFAULTS.center as [number, number]}
        zoom={MAP_DEFAULTS.zoom}
        minZoom={MAP_DEFAULTS.minZoom}
        maxZoom={MAP_DEFAULTS.maxZoom}
        maxBounds={bounds}
        maxBoundsViscosity={MAP_DEFAULTS.maxBoundsViscosity}
        worldCopyJump={false}
        preferCanvas
        zoomSnap={0.25}
        className={styles.map}
      >
        <MapResetController mapRef={mapRef} />
        <SelectedPointFocus point={selectedCoordinates} />

        <TileLayer
          key={basemapConfig.id}
          url={basemapConfig.url}
          attribution={basemapConfig.attribution}
          noWrap
        />

        {layerInfo ? (
          <TileLayer
            key={`tiles-${activeDate}`}
            url={tileUrl}
            opacity={opacity}
            noWrap
            eventHandlers={{
              tileerror(event: TileErrorEvent) {
                onTileError(`Missing tile ${event.coords.z}/${event.coords.x}/${event.coords.y}`);
              },
              load() {
                onTileError(null);
              },
            }}
          />
        ) : null}

        <GeoJSON
          data={provinces as GeoJSON.FeatureCollection}
          style={() => ({
            color: '#47627D',
            weight: 1,
            opacity: 0.45,
            fillOpacity: 0,
          })}
        />

        <PointsLayer
          points={points}
          activeDate={activeDate}
          selectedPointId={selectedPointId}
          onPointSelect={onPointSelect}
        />
      </MapContainer>

      <div className={styles.overlayTopLeft}>
        <MapControls
          activeDate={activeDate}
          availableDates={metadata.availableDates}
          opacity={opacity}
          basemap={basemap}
          onDateChange={onDateChange}
          onOpacityChange={onOpacityChange}
          onBasemapChange={setBasemap}
          onResetView={() => mapRef.current?.fitBounds(bounds, { padding: [16, 16] })}
        />
      </div>

      <div className={styles.overlayBottomLeft}>
        <MapLegend legend={legend} />
      </div>

      {hoverSample ? (
        <div className={styles.overlayBottomRight}>
          <div className={styles.hoverCard}>
            <strong>Grid Value</strong>
            <span>{formatDischarge(hoverSample.value)} {legend?.units ?? 'm³/s'}</span>
            <small>
              {hoverSample.lat.toFixed(2)}, {hoverSample.lon.toFixed(2)}
            </small>
          </div>
        </div>
      ) : null}
    </section>
  );
}
