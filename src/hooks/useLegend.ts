import { useEffect, useState } from 'react';
import type { LegendData } from '../types';
import { fetchLegend } from '../lib/api';

interface LegendState {
  legend: LegendData | null;
  isLoading: boolean;
  error: string | null;
}

export function useLegend(date: string | null | undefined): LegendState {
  const [legend, setLegend] = useState<LegendData | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    const targetDate = date ?? '';

    if (!targetDate) {
      setLegend(null);
      setError(null);
      setIsLoading(false);
      return;
    }

    async function load() {
      setIsLoading(true);
      setError(null);
      try {
        const nextLegend = await fetchLegend(targetDate);
        if (!cancelled) {
          setLegend(nextLegend);
        }
      } catch (loadError) {
        if (!cancelled) {
          setError(loadError instanceof Error ? loadError.message : 'Failed to load legend');
          setLegend(null);
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
  }, [date]);

  return { legend, isLoading, error };
}
