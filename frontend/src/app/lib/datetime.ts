export function parseBackendDateTime(value: string): Date | null {
  if (!value || typeof value !== 'string') return null;
  const normalized = value.trim();
  if (!normalized) return null;
  const date = normalized.endsWith('Z') ? new Date(normalized) : new Date(`${normalized}Z`);
  return Number.isNaN(date.getTime()) ? null : date;
}

export function toDateTimeLocalValue(value: string): string {
  const date = parseBackendDateTime(value);
  if (!date) return '';
  const local = new Date(date.getTime() - date.getTimezoneOffset() * 60 * 1000);
  return local.toISOString().slice(0, 16);
}

export function fromDateTimeLocalValue(value: string): string {
  if (!value) return '';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '';
  return date.toISOString();
}
