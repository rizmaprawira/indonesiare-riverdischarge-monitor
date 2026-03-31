import { useEffect, useState } from 'react';
import type { GridData } from '../types';
import { fetchGrid } from '../lib/api';

interface LayerGridState {
  grid: GridData | null;
  isLoading: boolean;
  error: string | null;
}

export function useLayerGrid(date: string | null | undefined): LayerGridState {
  const [grid, setGrid] = useState<GridData | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    const targetDate = date ?? '';

    if (!targetDate) {
      setGrid(null);
      setError(null);
      setIsLoading(false);
      return;
    }

    async function load() {
      setIsLoading(true);
      setError(null);
      try {
        const nextGrid = await fetchGrid(targetDate);
        if (!cancelled) {
          setGrid(nextGrid);
        }
      } catch (loadError) {
        if (!cancelled) {
          setGrid(null);
          setError(loadError instanceof Error ? loadError.message : 'Failed to load grid');
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

  return { grid, isLoading, error };
}
