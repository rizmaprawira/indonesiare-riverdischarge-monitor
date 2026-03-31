import type {
  DatasetBundle,
  GridData,
  HistoricalMetadata,
  LayersData,
  LegendData,
  PointsCollection,
  PointSeries,
  ProvincesCollection,
  RankingsData,
} from '../types';
import { DATA_PATHS } from './paths';

async function fetchJson<T>(url: string): Promise<T> {
  let response: Response;
  try {
    response = await fetch(url);
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    throw new Error(`Failed to fetch ${url}: ${message}`);
  }
  if (!response.ok) {
    throw new Error(`Failed to fetch ${url}: ${response.status} ${response.statusText}`);
  }
  try {
    return await response.json() as T;
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    throw new Error(`Failed to parse ${url}: ${message}`);
  }
}

export function fetchMetadata(): Promise<HistoricalMetadata> {
  return fetchJson<HistoricalMetadata>(DATA_PATHS.metadata);
}

export function fetchLayers(): Promise<LayersData> {
  return fetchJson<LayersData>(DATA_PATHS.layers);
}

export function fetchPoints(): Promise<PointsCollection> {
  return fetchJson<PointsCollection>(DATA_PATHS.points);
}

export function fetchRankings(): Promise<RankingsData> {
  return fetchJson<RankingsData>(DATA_PATHS.rankings);
}

export function fetchProvinces(): Promise<ProvincesCollection> {
  return fetchJson<ProvincesCollection>(DATA_PATHS.provinces);
}

export function fetchGrid(date: string): Promise<GridData> {
  return fetchJson<GridData>(DATA_PATHS.grid(date));
}

export function fetchLegend(date: string): Promise<LegendData> {
  return fetchJson<LegendData>(DATA_PATHS.legend(date));
}

export function fetchPointSeries(pointId: string): Promise<PointSeries> {
  return fetchJson<PointSeries>(DATA_PATHS.pointSeries(pointId));
}

export async function fetchDatasetBundle(): Promise<DatasetBundle> {
  const [metadata, layers, points, rankings, provinces] = await Promise.all([
    fetchMetadata(),
    fetchLayers(),
    fetchPoints(),
    fetchRankings(),
    fetchProvinces(),
  ]);

  return { metadata, layers, points, rankings, provinces };
}
