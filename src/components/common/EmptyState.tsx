import styles from './EmptyState.module.css';

interface EmptyStateProps {
  title: string;
  message: string;
  actionLabel?: string;
  onAction?: () => void;
}

export function EmptyState({ title, message, actionLabel, onAction }: EmptyStateProps) {
  return (
    <div className={styles.wrapper}>
      <div className={styles.card}>
        <span className={styles.kicker}>IndonesiaRe Industry Research</span>
        <h1 className={styles.title}>{title}</h1>
        <p className={styles.message}>{message}</p>
        {actionLabel && onAction ? (
          <button className={styles.button} onClick={onAction}>
            {actionLabel}
          </button>
        ) : null}
      </div>
    </div>
  );
}
