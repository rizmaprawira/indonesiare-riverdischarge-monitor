import type { PointSeries } from '../types';

export function pointSeriesToCsv(series: PointSeries): string {
  const headers = ['Date', 'Discharge (m³/s)'];
  const rows = series.dates.map((date, index) => {
    const value = series.values[index];
    return [date, value !== null && value !== undefined ? value : ''];
  });

  return [headers, ...rows]
    .map((row) => row.map((value) => `${value}`).join(','))
    .join('\n');
}

export function downloadTextFile(content: string, filename: string): void {
  const blob = new Blob([content], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}
