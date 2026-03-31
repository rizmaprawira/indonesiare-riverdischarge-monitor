import type { HistoricalMetadata, PointFeature } from '../../types';
import { usePointSeries } from '../../hooks/usePointSeries';
import { downloadTextFile, pointSeriesToCsv } from '../../lib/csv';
import { formatDate, formatDischarge } from '../../lib/format';
import { Hydrograph } from './Hydrograph';
import styles from './DetailPanel.module.css';

interface DetailPanelProps {
  point: PointFeature | null;
  metadata: HistoricalMetadata;
  onClose: () => void;
}

export function DetailPanel({ point, metadata, onClose }: DetailPanelProps) {
  const pointId = point?.properties?.id ?? null;
  const { series, isLoading, error } = usePointSeries(pointId);

  return (
    <aside className={point ? styles.panelOpen : styles.panel}>
      <div className={styles.inner}>
        <div className={styles.header}>
          <div>
            <span className={styles.eyebrow}>Point Detail</span>
            <h2 className={styles.title}>{point?.properties?.id ?? 'No point selected'}</h2>
            <p className={styles.subtitle}>
              {point?.properties?.label ?? point?.properties?.province ?? 'Select a point on the map or ranking table.'}
            </p>
          </div>
          <button className={styles.closeButton} onClick={onClose}>
            Close
          </button>
        </div>

        {!point ? (
          <p className={styles.placeholder}>Choose a monitoring point to inspect the 10-day historical discharge and export the data series.</p>
        ) : isLoading ? (
          <p className={styles.placeholder}>Loading point data…</p>
        ) : error ? (
          <div className={styles.errorState}>
            <strong>Point series unavailable</strong>
            <p>{error}</p>
          </div>
        ) : series ? (
          <>
            <div className={styles.metaGrid}>
              <div className={styles.metaCard}>
                <span className={styles.metaLabel}>Data Range</span>
                <strong>{formatDate(metadata.oldestDate)} – {formatDate(metadata.latestDate)}</strong>
              </div>
              <div className={styles.metaCard}>
                <span className={styles.metaLabel}>Coordinates</span>
                <strong>
                  {point.properties?.lat?.toFixed(2)}, {point.properties?.lon?.toFixed(2)}
                </strong>
              </div>
              <div className={styles.metaCard}>
                <span className={styles.metaLabel}>Province</span>
                <strong>{point.properties?.province ?? 'Unknown'}</strong>
              </div>
              <div className={styles.metaCard}>
                <span className={styles.metaLabel}>Max Discharge</span>
                <strong>{formatDischarge(series.summary.max)}</strong>
              </div>
            </div>

            <div className={styles.chartBlock}>
              <Hydrograph series={series} />
            </div>

            <div className={styles.statsGrid}>
              <div className={styles.stat}>
                <span>Min</span>
                <strong>{formatDischarge(series.summary.min)}</strong>
              </div>
              <div className={styles.stat}>
                <span>Mean</span>
                <strong>{formatDischarge(series.summary.mean)}</strong>
              </div>
              <div className={styles.stat}>
                <span>Max</span>
                <strong>{formatDischarge(series.summary.max)}</strong>
              </div>
              <div className={styles.stat}>
                <span>Days</span>
                <strong>{series.dates.length}</strong>
              </div>
            </div>

            <button
              className={styles.downloadButton}
              onClick={() => {
                const csv = pointSeriesToCsv(series);
                downloadTextFile(csv, `${series.pointId}_historical.csv`);
              }}
            >
              Download CSV
            </button>
          </>
        ) : null}
      </div>
    </aside>
  );
}
