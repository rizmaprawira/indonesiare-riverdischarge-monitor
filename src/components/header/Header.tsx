import logoIcon from '../../assets/header-logo-icon.png';
import logoText from '../../assets/header-logo-text.png';
import type { DateKey, HistoricalMetadata } from '../../types';
import { formatDate, formatTimestamp } from '../../lib/format';
import styles from './Header.module.css';

interface HeaderProps {
  metadata: HistoricalMetadata;
  activeDate: DateKey;
  stale: boolean;
  tileError: string | null;
}

export function Header({ metadata, activeDate, stale, tileError }: HeaderProps) {
  return (
    <header className={styles.header}>
      <div className={styles.brand}>
        <img className={styles.logoText} src={logoText} alt="IndonesiaRe Institute" />
        <img className={styles.logoIcon} src={logoIcon} alt="IndonesiaRe" />
        <div className={styles.brandCopy}>
          <span className={styles.eyebrow}>Industry Research</span>
          <strong className={styles.title}>Indonesia River Discharge Monitoring</strong>
        </div>
      </div>

      <div className={styles.metaStrip}>
        <div className={styles.metaCard}>
          <span className={styles.metaLabel}>Data Type</span>
          <strong>Historical</strong>
        </div>
        <div className={styles.metaCard}>
          <span className={styles.metaLabel}>Latest Date</span>
          <strong>{formatDate(metadata.latestDate)}</strong>
        </div>
        <div className={styles.metaCard}>
          <span className={styles.metaLabel}>Active Layer</span>
          <strong>{formatDate(activeDate)}</strong>
        </div>
        <div className={styles.metaCard}>
          <span className={styles.metaLabel}>Updated</span>
          <strong>{formatTimestamp(metadata.generatedAt)}</strong>
        </div>
      </div>

      <div className={styles.statuses}>
        <span className={styles.badgeInfo}>Historical</span>
        {stale ? <span className={styles.badgeWarning}>Stale Data</span> : null}
        {tileError ? <span className={styles.badgeError}>Tile Issue</span> : null}
      </div>
    </header>
  );
}
