const DATE_FORMAT = new Intl.DateTimeFormat('en-GB', {
  day: '2-digit',
  month: 'short',
  year: 'numeric',
});

const DATE_SHORT_FORMAT = new Intl.DateTimeFormat('en-GB', {
  day: '2-digit',
  month: 'short',
});

const TIMESTAMP_FORMAT = new Intl.DateTimeFormat('en-GB', {
  day: '2-digit',
  month: 'short',
  year: 'numeric',
  hour: '2-digit',
  minute: '2-digit',
  timeZoneName: 'short',
});

export function formatDate(value: string): string {
  return DATE_FORMAT.format(new Date(value));
}

export function formatDateShort(value: string): string {
  return DATE_SHORT_FORMAT.format(new Date(value));
}

export function formatTimestamp(value: string): string {
  return TIMESTAMP_FORMAT.format(new Date(value));
}

export function formatDischarge(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return 'No data';
  }

  return new Intl.NumberFormat('en-US', {
    maximumFractionDigits: value >= 100 ? 0 : 1,
  }).format(value);
}

export function isDataStale(generatedAt: string, staleAfterHours: number): boolean {
  const generated = new Date(generatedAt).getTime();
  return Date.now() - generated > staleAfterHours * 60 * 60 * 1000;
}
