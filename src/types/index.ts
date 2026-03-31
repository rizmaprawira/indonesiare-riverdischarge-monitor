import type { Feature, FeatureCollection, Point, MultiPolygon, Polygon } from 'geojson';

/** Available historical dates (ISO format) */
export type DateKey = string; // e.g., "2026-03-20"

/** Metadata about the historical dataset */
export interface HistoricalMetadata {
  mode: 'historical';
  dataSource: string;
  latestDate: string;
  oldestDate: string;
  availableDates: string[];
  generatedAt: string;
  lagDays: number;
  units: string;
}

/** Layer info for a single date */
export interface LayerInfo {
  date: string;
  label: string;
  tileUrl: string;
  gridUrl: string;
  legendUrl: string;
  minValue: number;
  maxValue: number;
}

/** All available layers indexed by date */
export interface LayersData {
  layers: Record<string, LayerInfo>;
  defaultDate: string;
}

/** Properties attached to each monitoring point */
export interface PointProperties {
  id: string;
  label: string;
  province: string;
  lat: number;
  lon: number;
  /** Discharge value per date */
  values: Record<string, number | null>;
  /** Summary statistics */
  summary: {
    min: number;
    max: number;
    mean: number;
  };
  /** Rank for the latest date */
  rank?: number;
}

/** GeoJSON Feature for a monitoring point */
export type PointFeature = Feature<Point, PointProperties>;

/** Collection of all monitoring points */
export type PointsCollection = FeatureCollection<Point, PointProperties>;

/** Time series data for a single point */
export interface PointSeries {
  pointId: string;
  dates: string[];
  values: number[];
  summary: {
    min: number;
    max: number;
    mean: number;
  };
}

/** Top-ranked points for a date */
export interface TopPoints {
  date: string;
  points: Array<{
    id: string;
    label: string;
    province: string;
    value: number;
    rank: number;
  }>;
}

/** Rankings for all dates */
export type RankingsData = Record<string, TopPoints>;

/** Grid data for hover sampling */
export interface GridData {
  date: string;
  units: string;
  lats: number[];
  lons: number[];
  values: (number | null)[][];
}

/** Legend colorbar data */
export interface LegendData {
  date: string;
  units: string;
  stops: Array<{
    value: number;
    color: string;
    label: string;
  }>;
}

/** Province boundary feature */
export type ProvinceFeature = Feature<Polygon | MultiPolygon, {
  name: string;
  code?: string;
}>;

/** Province boundaries collection */
export type ProvincesCollection = FeatureCollection<Polygon | MultiPolygon, {
  name: string;
  code?: string;
}>;

/** Complete dataset loaded by useDataset hook */
export interface DatasetBundle {
  metadata: HistoricalMetadata;
  layers: LayersData;
  points: PointsCollection;
  rankings: RankingsData;
  provinces: ProvincesCollection;
}

/** Basemap configuration */
export interface BasemapConfig {
  id: string;
  name: string;
  url: string;
  attribution: string;
  default?: boolean;
}

/** App configuration */
export interface AppConfig {
  siteName: string;
  organization: string;
  department: string;
  version: string;
  indonesiaBounds: {
    north: number;
    south: number;
    west: number;
    east: number;
  };
  mapDefaults: {
    center: [number, number];
    zoom: number;
    minZoom: number;
    maxZoom: number;
    maxBoundsViscosity: number;
  };
  basemaps: BasemapConfig[];
  defaultDate: string;
  defaultOpacity: number;
  staleAfterHours: number;
  topPointsCount: number;
  summaryPanelWidth: number;
  detailPanelWidth: number;
}

/** Style configuration */
export interface StyleConfig {
  colors: {
    brand: Record<string, string>;
    surface: Record<string, string>;
    text: Record<string, string>;
    status: Record<string, string>;
  };
  typography: {
    uiFontFamily: string;
    monoFontFamily: string;
  };
  dischargeColorRamp: {
    scale: 'log' | 'linear';
    units: string;
    stops: Array<{
      value: number;
      color: string;
      label: string;
    }>;
    noDataColor: string;
  };
  markers: {
    radius: number;
    stroke: string;
    fill: string;
    selected: string;
  };
  layout: {
    headerHeight: number;
    panelRadius: number;
    shadow: string;
  };
}
