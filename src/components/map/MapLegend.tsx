import type { LegendData } from '../../types';
import { formatDischarge } from '../../lib/format';
import styles from './MapLegend.module.css';

interface MapLegendProps {
  legend: LegendData | null;
}

export function MapLegend({ legend }: MapLegendProps) {
  if (!legend) {
    return null;
  }

  const gradient = `linear-gradient(180deg, ${[...legend.stops]
    .reverse()
    .map((stop) => stop.color)
    .join(', ')})`;

  return (
    <div className={styles.legend}>
      <div className={styles.header}>
        <strong>Discharge Legend</strong>
        <span>{legend.units}</span>
      </div>
      <p className={styles.description}>Mean river discharge in the last 24 hours</p>
      <div className={styles.colorbarWrap}>
        <div className={styles.colorbar} style={{ background: gradient }} />
        <div className={styles.tickLabels}>
          {[...legend.stops].reverse().map((stop) => (
            <span className={styles.label} key={`${legend.date}-${stop.value}`}>
              {stop.label}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}
