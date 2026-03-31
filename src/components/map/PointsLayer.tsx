import { useEffect, useRef } from 'react';
import { useMap } from 'react-leaflet';
import L from 'leaflet';
import type { DateKey, PointFeature, PointsCollection } from '../../types';
import { formatDischarge } from '../../lib/format';

interface PointsLayerProps {
  points: PointsCollection;
  activeDate: DateKey;
  selectedPointId: string | null;
  onPointSelect: (pointId: string) => void;
}

function getColor(value: number | null, selected: boolean): string {
  if (selected) {
    return '#C7333A';
  }
  if (value === null) {
    return '#256F86';
  }
  if (value >= 5000) {
    return '#B7373B';
  }
  if (value >= 1000) {
    return '#1D3E7B';
  }
  if (value >= 250) {
    return '#2A6EAA';
  }
  return '#256F86';
}

export function PointsLayer({
  points,
  activeDate,
  selectedPointId,
  onPointSelect,
}: PointsLayerProps) {
  const map = useMap();
  const layerRef = useRef<L.GeoJSON | null>(null);
  const markerRef = useRef<Map<string, L.CircleMarker>>(new Map());

  useEffect(() => {
    const renderer = L.canvas({ padding: 0.5 });

    if (layerRef.current) {
      map.removeLayer(layerRef.current);
      markerRef.current.clear();
    }

    const layer = L.geoJSON(points as GeoJSON.FeatureCollection, {
      pointToLayer(feature, latlng) {
        const pointFeature = feature as unknown as PointFeature;
        const props = pointFeature.properties;
        const value = props?.values?.[activeDate] ?? null;
        const isSelected = props?.id === selectedPointId;

        const marker = L.circleMarker(latlng, {
          radius: isSelected ? 7 : 4.5,
          fillColor: getColor(value, isSelected),
          fillOpacity: isSelected ? 0.96 : 0.84,
          color: '#F7FAFC',
          weight: isSelected ? 2.5 : 1.5,
          opacity: 0.95,
          renderer,
        });

        if (props?.id) {
          markerRef.current.set(props.id, marker);
        }
        return marker;
      },
      onEachFeature(feature, layerInstance) {
        const pointFeature = feature as unknown as PointFeature;
        const props = pointFeature.properties;
        const value = props?.values?.[activeDate] ?? null;
        const label = props?.label ?? props?.province ?? 'Monitoring point';
        const tooltip = `
          <div>
            <strong>${props?.id ?? 'Unknown'}</strong><br />
            <span>${label}</span><br />
            <span>${formatDischarge(value)} m³/s</span>
          </div>
        `;

        layerInstance.bindTooltip(tooltip, {
          className: 'point-tooltip',
          direction: 'top',
          offset: [0, -8],
        });

        layerInstance.on('click', () => {
          if (props?.id) {
            onPointSelect(props.id);
          }
        });
        layerInstance.on('mouseover', () => {
          const marker = layerInstance as L.CircleMarker;
          if (props?.id !== selectedPointId) {
            marker.setStyle({
              radius: 6,
              fillOpacity: 0.96,
            });
          }
        });
        layerInstance.on('mouseout', () => {
          const marker = layerInstance as L.CircleMarker;
          const val = props?.values?.[activeDate] ?? null;
          const isSelected = props?.id === selectedPointId;
          marker.setStyle({
            radius: isSelected ? 7 : 4.5,
            fillColor: getColor(val, isSelected),
            fillOpacity: isSelected ? 0.96 : 0.84,
          });
        });
      },
    });

    layer.addTo(map);
    layerRef.current = layer;

    return () => {
      if (layerRef.current) {
        map.removeLayer(layerRef.current);
      }
    };
  }, [activeDate, map, onPointSelect, points, selectedPointId]);

  useEffect(() => {
    for (const feature of points.features) {
      const props = feature.properties;
      if (!props?.id) continue;
      const marker = markerRef.current.get(props.id);
      if (!marker) {
        continue;
      }
      const value = props.values?.[activeDate] ?? null;
      const isSelected = props.id === selectedPointId;
      marker.setStyle({
        radius: isSelected ? 7 : 4.5,
        fillColor: getColor(value, isSelected),
        fillOpacity: isSelected ? 0.96 : 0.84,
      });
      if (isSelected) {
        marker.bringToFront();
      }
    }
  }, [activeDate, points, selectedPointId]);

  return null;
}
