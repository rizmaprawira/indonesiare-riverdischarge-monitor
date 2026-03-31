export function resolveBasePath(path: string): string {
  if (/^https?:\/\//.test(path)) {
    return path;
  }

  if (typeof window !== 'undefined' && window.location.protocol === 'file:') {
    return path.startsWith('/') ? path.slice(1) : path;
  }

  const baseUrl = import.meta.env.BASE_URL || '/';
  const normalizedBase = baseUrl.endsWith('/') ? baseUrl : `${baseUrl}/`;
  const normalizedPath = path.startsWith('/') ? path.slice(1) : path;

  return `${normalizedBase}${normalizedPath}`;
}

export const DATA_PATHS = {
  metadata: resolveBasePath('data/latest/metadata.json'),
  layers: resolveBasePath('data/latest/layers.json'),
  points: resolveBasePath('data/latest/points.geojson'),
  rankings: resolveBasePath('data/latest/rankings.json'),
  provinces: resolveBasePath('data/latest/boundaries/provinces.geojson'),
  pointSeries: (pointId: string) => resolveBasePath(`data/latest/series/${pointId}.json`),
  grid: (date: string) => resolveBasePath(`data/latest/grids/${date}.json`),
  legend: (date: string) => resolveBasePath(`data/latest/legends/${date}.json`),
  tiles: (date: string) => resolveBasePath(`data/latest/tiles/${date}/control/{z}/{x}/{y}.png`),
};
