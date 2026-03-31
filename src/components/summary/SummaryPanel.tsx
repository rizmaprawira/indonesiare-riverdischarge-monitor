import { useDeferredValue, useMemo, useState } from 'react';
import type { DateKey, HistoricalMetadata, PointsCollection, TopPoints } from '../../types';
import { formatDate, formatDischarge, formatTimestamp } from '../../lib/format';
import styles from './SummaryPanel.module.css';

interface SummaryPanelProps {
  metadata: HistoricalMetadata;
  points: PointsCollection;
  activeDate: DateKey;
  stale: boolean;
  ranking: TopPoints['points'];
  selectedPointId: string | null;
  onPointSelect: (pointId: string) => void;
}

type SortKey = 'rank' | 'value' | 'id';

export function SummaryPanel({
  metadata,
  points,
  activeDate,
  stale,
  ranking,
  selectedPointId,
  onPointSelect,
}: SummaryPanelProps) {
  const [collapsed, setCollapsed] = useState(false);
  const [query, setQuery] = useState('');
  const [sortKey, setSortKey] = useState<SortKey>('rank');
  const deferredQuery = useDeferredValue(query);

  const matches = useMemo(() => {
    const normalized = deferredQuery.trim().toLowerCase();
    if (!normalized) {
      return [];
    }

    return points.features
      .filter((feature) => feature.properties?.id?.toLowerCase().includes(normalized))
      .slice(0, 8);
  }, [deferredQuery, points.features]);

  const orderedRanking = useMemo(() => {
    const slice = [...ranking];

    if (sortKey === 'value') {
      slice.sort((left, right) => (right.value ?? -1) - (left.value ?? -1));
    } else if (sortKey === 'id') {
      slice.sort((left, right) => left.id.localeCompare(right.id));
    } else {
      slice.sort((left, right) => left.rank - right.rank);
    }

    return slice;
  }, [ranking, sortKey]);

  if (collapsed) {
    return (
      <button className={styles.revealButton} onClick={() => setCollapsed(false)}>
        Summary
      </button>
    );
  }

  return (
    <aside className={styles.panel}>
      <div className={styles.header}>
        <div>
          <span className={styles.eyebrow}>Historical Summary</span>
          <h2 className={styles.title}>Indonesia Coverage</h2>
        </div>
        <button className={styles.collapseButton} onClick={() => setCollapsed(true)}>
          Hide
        </button>
      </div>

      <div className={styles.cardGrid}>
        <div className={styles.card}>
          <span className={styles.cardLabel}>Data Range</span>
          <strong>{formatDate(metadata.oldestDate)} – {formatDate(metadata.latestDate)}</strong>
          <span className={styles.cardMeta}>{metadata.availableDates.length} days</span>
        </div>
        <div className={styles.card}>
          <span className={styles.cardLabel}>Active Date</span>
          <strong>{formatDate(activeDate)}</strong>
          <span className={styles.cardMeta}>Historical discharge</span>
        </div>
        <div className={styles.card}>
          <span className={styles.cardLabel}>Monitoring Points</span>
          <strong>{points.features.length}</strong>
          <span className={styles.cardMeta}>Across all provinces</span>
        </div>
        <div className={styles.card}>
          <span className={styles.cardLabel}>Status</span>
          <strong>{stale ? 'Check freshness' : 'Current package'}</strong>
          <span className={styles.cardMeta}>{formatTimestamp(metadata.generatedAt)}</span>
        </div>
      </div>

      <div className={styles.section}>
        <div className={styles.sectionHeader}>
          <h3>Point Search</h3>
        </div>
        <input
          className={styles.search}
          type="text"
          placeholder="Search by point ID"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
        />
        {matches.length > 0 ? (
          <div className={styles.matchList}>
            {matches.map((match) => (
              <button
                key={match.properties?.id}
                className={match.properties?.id === selectedPointId ? styles.matchActive : styles.match}
                onClick={() => match.properties?.id && onPointSelect(match.properties.id)}
              >
                <span>{match.properties?.id}</span>
                <small>{match.properties?.label ?? match.properties?.province ?? 'Monitoring point'}</small>
              </button>
            ))}
          </div>
        ) : deferredQuery ? (
          <p className={styles.helper}>No matching monitoring point.</p>
        ) : (
          <p className={styles.helper}>Type a monitoring point id such as `IDN_...`.</p>
        )}
      </div>

      <div className={styles.section}>
        <div className={styles.sectionHeader}>
          <h3>Highest Discharge Points</h3>
          <select className={styles.sortSelect} value={sortKey} onChange={(event) => setSortKey(event.target.value as SortKey)}>
            <option value="rank">Rank</option>
            <option value="value">Value</option>
            <option value="id">Point ID</option>
          </select>
        </div>

        <div className={styles.table}>
          {orderedRanking.map((entry) => (
            <button
              key={`${activeDate}-${entry.id}`}
              className={entry.id === selectedPointId ? styles.rowActive : styles.row}
              onClick={() => onPointSelect(entry.id)}
            >
              <span className={styles.rank}>{entry.rank}</span>
              <span className={styles.point}>
                <strong>{entry.id}</strong>
                <small>{entry.province ?? entry.label}</small>
              </span>
              <span className={styles.value}>{formatDischarge(entry.value)}</span>
            </button>
          ))}
        </div>
      </div>
    </aside>
  );
}
