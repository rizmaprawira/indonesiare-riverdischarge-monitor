import type { DateKey } from '../../types';
import { BASEMAPS } from '../../lib/constants';
import { formatDateShort } from '../../lib/format';
import styles from './MapControls.module.css';

interface MapControlsProps {
  activeDate: DateKey;
  availableDates: string[];
  opacity: number;
  basemap: string;
  onDateChange: (date: DateKey) => void;
  onOpacityChange: (value: number) => void;
  onBasemapChange: (basemap: string) => void;
  onResetView: () => void;
}

export function MapControls({
  activeDate,
  availableDates,
  opacity,
  basemap,
  onDateChange,
  onOpacityChange,
  onBasemapChange,
  onResetView,
}: MapControlsProps) {
  return (
    <div className={styles.controls}>
      <div className={styles.card}>
        <span className={styles.label}>Historical Date</span>
        <select
          className={styles.select}
          value={activeDate}
          onChange={(event) => onDateChange(event.target.value)}
        >
          {availableDates.map((date) => (
            <option key={date} value={date}>
              {formatDateShort(date)} {date === availableDates[availableDates.length - 1] ? '(Latest)' : ''}
            </option>
          ))}
        </select>
      </div>

      <div className={styles.card}>
        <span className={styles.label}>Overlay Opacity</span>
        <input
          className={styles.slider}
          type="range"
          min={0.2}
          max={1}
          step={0.02}
          value={opacity}
          onChange={(event) => onOpacityChange(Number(event.target.value))}
        />
      </div>

      <div className={styles.card}>
        <span className={styles.label}>Basemap</span>
        <select className={styles.select} value={basemap} onChange={(event) => onBasemapChange(event.target.value)}>
          {BASEMAPS.map((option) => (
            <option key={option.id} value={option.id}>
              {option.name}
            </option>
          ))}
        </select>
      </div>

      <button className={styles.resetButton} onClick={onResetView}>
        Reset Indonesia View
      </button>
    </div>
  );
}
