import { useEffect, useState } from 'react';
import type { DatasetBundle } from '../types';
import { fetchDatasetBundle } from '../lib/api';

interface DatasetState {
  data: DatasetBundle | null;
  isLoading: boolean;
  error: string | null;
  refetch: () => void;
}

export function useDataset(): DatasetState {
  const [data, setData] = useState<DatasetBundle | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [reloadToken, setReloadToken] = useState(0);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setIsLoading(true);
      setError(null);

      try {
        const bundle = await fetchDatasetBundle();

        if (!cancelled) {
          setData(bundle);
        }
      } catch (loadError) {
        if (!cancelled) {
          setError(loadError instanceof Error ? loadError.message : 'Failed to load dataset');
          setData(null);
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
  }, [reloadToken]);

  return {
    data,
    isLoading,
    error,
    refetch: () => setReloadToken((value) => value + 1),
  };
}
