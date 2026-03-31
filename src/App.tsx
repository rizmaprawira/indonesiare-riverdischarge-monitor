import { startTransition, useMemo, useState } from 'react';
import type { DateKey } from './types';
import { DEFAULT_DATE, DEFAULT_OPACITY } from './lib/constants';
import { buildPointIndex, getLayerInfo, getRankingForDate } from './lib/selectors';
import { isDataStale } from './lib/format';
import { useDataset } from './hooks/useDataset';
import { useLegend } from './hooks/useLegend';
import { Header } from './components/header/Header';
import { SummaryPanel } from './components/summary/SummaryPanel';
import { MapView } from './components/map/MapView';
import { DetailPanel } from './components/detail/DetailPanel';
import { EmptyState } from './components/common/EmptyState';
import styles from './App.module.css';

function App() {
  const { data, isLoading, error, refetch } = useDataset();
  const [activeDate, setActiveDate] = useState<DateKey>(DEFAULT_DATE);
  const [opacity, setOpacity] = useState<number>(DEFAULT_OPACITY);
  const [selectedPointId, setSelectedPointId] = useState<string | null>(null);
  const [tileError, setTileError] = useState<string | null>(null);

  // Update active date when data loads
  const effectiveDate = data?.metadata.latestDate ?? activeDate;
  const currentActiveDate = data?.metadata.availableDates.includes(activeDate) ? activeDate : effectiveDate;

  const pointIndex = useMemo(() => buildPointIndex(data?.points ?? null), [data?.points]);
  const selectedPoint = selectedPointId ? pointIndex.get(selectedPointId) ?? null : null;
  const activeLayerInfo = getLayerInfo(data?.layers ?? null, currentActiveDate);
  const { legend } = useLegend(currentActiveDate);
  const rankingSlice = getRankingForDate(data?.rankings ?? null, currentActiveDate);
  const stale = data ? isDataStale(data.metadata.generatedAt, 72) : false;

  function handlePointSelect(pointId: string | null) {
    startTransition(() => {
      setSelectedPointId(pointId);
    });
  }

  function handleDateChange(date: DateKey) {
    setActiveDate(date);
  }

  if (isLoading) {
    return <EmptyState title="Loading historical data" message="Reading the latest static discharge assets." />;
  }

  if (error || !data) {
    return (
      <EmptyState
        title="Data package unavailable"
        message={error ?? 'The static dataset could not be loaded.'}
        actionLabel="Retry"
        onAction={refetch}
      />
    );
  }

  return (
    <div className={styles.appShell}>
      <Header
        metadata={data.metadata}
        activeDate={currentActiveDate}
        stale={stale}
        tileError={tileError}
      />

      <main className={styles.stage}>
        <MapView
          metadata={data.metadata}
          layers={data.layers}
          points={data.points}
          provinces={data.provinces}
          activeDate={currentActiveDate}
          opacity={opacity}
          selectedPointId={selectedPointId}
          onPointSelect={handlePointSelect}
          onTileError={setTileError}
          onDateChange={handleDateChange}
          onOpacityChange={setOpacity}
          legend={legend}
        />

        <SummaryPanel
          metadata={data.metadata}
          points={data.points}
          activeDate={currentActiveDate}
          stale={stale}
          ranking={rankingSlice}
          selectedPointId={selectedPointId}
          onPointSelect={handlePointSelect}
        />

        <DetailPanel
          point={selectedPoint}
          metadata={data.metadata}
          onClose={() => handlePointSelect(null)}
        />
      </main>
    </div>
  );
}

export default App;
