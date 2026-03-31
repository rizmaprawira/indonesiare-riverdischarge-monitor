import type {
  LayersData,
  LayerInfo,
  PointFeature,
  PointsCollection,
  RankingsData,
  TopPoints,
} from '../types';

export function getLayerInfo(
  layers: LayersData | null,
  date: string,
): LayerInfo | null {
  if (!layers) {
    return null;
  }
  return layers.layers[date] ?? null;
}

export function getRankingForDate(
  rankings: RankingsData | null,
  date: string,
): TopPoints['points'] {
  return rankings?.[date]?.points ?? [];
}

export function buildPointIndex(points: PointsCollection | null): Map<string, PointFeature> {
  const index = new Map<string, PointFeature>();
  if (!points) {
    return index;
  }

  for (const feature of points.features) {
    if (feature.properties?.id) {
      index.set(feature.properties.id, feature);
    }
  }

  return index;
}

export function getPointValue(
  point: PointFeature | undefined,
  date: string,
): number | null {
  if (!point?.properties?.values) {
    return null;
  }
  return point.properties.values[date] ?? null;
}
