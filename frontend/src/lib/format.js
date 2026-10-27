// Formateo para la UI (es-AR). Las fechas de la API vienen en ISO 8601; las "date" (YYYY-MM-DD) se tratan como fecha local.

export const TZ = 'America/Argentina/Buenos_Aires';

/** 'YYYY-MM-DD' -> Date local (sin corrimiento por zona horaria). */
export function parseDay(day) {
  if (!day) return null;
  if (day instanceof Date) return day;
  const [y, m, d] = String(day).slice(0, 10).split('-').map(Number);
  return new Date(y, m - 1, d);
}

/** Date -> 'YYYY-MM-DD' local. */
export function toDay(date) {
  const d = date instanceof Date ? date : new Date(date);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}

export const todayDay = () => toDay(new Date());

const MONTHS = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre'];
const MONTHS_SHORT = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic'];
const WEEKDAYS = ['domingo', 'lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado'];
export const WEEKDAY_ES = {
  MONDAY: 'Lunes', TUESDAY: 'Martes', WEDNESDAY: 'Miércoles', THURSDAY: 'Jueves', FRIDAY: 'Viernes', SATURDAY: 'Sábado', SUNDAY: 'Domingo',
};

export { MONTHS, MONTHS_SHORT, WEEKDAYS };

/** '2026-10-14' -> '14 de octubre de 2026' */
export function longDate(day) {
  const d = parseDay(day);
  return d ? `${d.getDate()} de ${MONTHS[d.getMonth()]} de ${d.getFullYear()}` : '—';
}

/** '2026-10-14' -> '14/10/2026' */
export function shortDate(day) {
  const d = parseDay(day);
  return d ? `${String(d.getDate()).padStart(2, '0')}/${String(d.getMonth() + 1).padStart(2, '0')}/${d.getFullYear()}` : '—';
}

/** '2026-10-14' -> 'miércoles 14 de octubre' */
export function weekdayDate(day) {
  const d = parseDay(day);
  return d ? `${WEEKDAYS[d.getDay()]} ${d.getDate()} de ${MONTHS[d.getMonth()]}` : '—';
}

/** ISO datetime -> Date in Buenos Aires parts. */
export function dateTimeParts(iso) {
  if (!iso) return null;
  const d = new Date(iso);
  const f = new Intl.DateTimeFormat('es-AR', {
    timeZone: TZ, year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', hour12: false,
  }).formatToParts(d);
  const get = (t) => f.find((p) => p.type === t)?.value;
  return { day: `${get('year')}-${get('month')}-${get('day')}`, time: `${get('hour')}:${get('minute')}` };
}

/** ISO datetime -> '25/08/2026' */
export const isoShortDate = (iso) => (iso ? shortDate(dateTimeParts(iso).day) : '—');
/** ISO datetime -> '12:34' */
export const isoTime = (iso) => (iso ? dateTimeParts(iso).time : '—');
/** ISO datetime -> '14 de octubre de 2026' */
export const isoLongDate = (iso) => (iso ? longDate(dateTimeParts(iso).day) : '—');

/** "Hace 5 min", "Hace 2 h", "Ayer", "12/10/2026" */
export function relativeTime(iso) {
  if (!iso) return '';
  const diff = (Date.now() - new Date(iso).getTime()) / 1000;
  if (diff < 60) return 'Hace instantes';
  if (diff < 3600) return `Hace ${Math.floor(diff / 60)} min`;
  if (diff < 86400) return `Hace ${Math.floor(diff / 3600)} h`;
  if (diff < 172800) return 'Ayer';
  if (diff < 604800) return `Hace ${Math.floor(diff / 86400)} días`;
  return isoShortDate(iso);
}

/** "15000.00" -> "$15.000" (o "$15.000,50" si tiene centavos). */
export function money(value, { sign = false } = {}) {
  const n = Number(value) || 0;
  const abs = Math.abs(n);
  const cents = Math.round(abs * 100) % 100 !== 0;
  const s = abs.toLocaleString('es-AR', { minimumFractionDigits: cents ? 2 : 0, maximumFractionDigits: 2 });
  const prefix = sign ? (n < 0 ? '− ' : '+ ') : n < 0 ? '-' : '';
  return `${prefix}$${s}`;
}

/** Nota numérica -> "8" / "7,5" / "—" */
export function grade(value) {
  if (value === null || value === undefined || value === '') return '—';
  const n = Number(value);
  return Number.isInteger(n) ? String(n) : n.toLocaleString('es-AR', { maximumFractionDigits: 2 });
}

export function percent(value) {
  if (value === null || value === undefined) return '—';
  return `${Math.round(Number(value))}%`;
}

export function initials(name) {
  return (name || '')
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((p) => p[0].toUpperCase())
    .join('');
}

export function minutesToLabel(min) {
  if (!min) return '—';
  const h = Math.floor(min / 60);
  const m = min % 60;
  if (!h) return `${m} min`;
  return m ? `${h} h ${m} min` : `${h} h`;
}

export function uuid() {
  if (globalThis.crypto?.randomUUID) return globalThis.crypto.randomUUID();
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    return (c === 'x' ? r : (r & 0x3) | 0x8).toString(16);
  });
}

/** "40123456" -> "40.123.456" */
export function dni(value) {
  const s = String(value || '').replace(/\D/g, '');
  return s ? s.replace(/\B(?=(\d{3})+(?!\d))/g, '.') : '—';
}
