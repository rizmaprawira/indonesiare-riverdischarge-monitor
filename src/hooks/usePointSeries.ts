import { useEffect, useState } from 'react';
import type { PointSeries } from '../types';
import { fetchPointSeries } from '../lib/api';

interface PointSeriesState {
  series: PointSeries | null;
  isLoading: boolean;
  error: string | null;
}

export function usePointSeries(pointId: string | null): PointSeriesState {
  const [series, setSeries] = useState<PointSeries | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    const targetPointId = pointId ?? '';

    if (!targetPointId) {
      setSeries(null);
      setError(null);
      setIsLoading(false);
      return;
    }

    async function load() {
      setIsLoading(true);
      setError(null);

      try {
        const nextSeries = await fetchPointSeries(targetPointId);
        if (!cancelled) {
          setSeries(nextSeries);
        }
      } catch (loadError) {
        if (!cancelled) {
          setSeries(null);
          setError(loadError instanceof Error ? loadError.message : 'Failed to load point series');
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    }

    load();

    return () => {
      cancelled = true;
    };
  }, [pointId]);

  return { series, isLoading, error };
}
