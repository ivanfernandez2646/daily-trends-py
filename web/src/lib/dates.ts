/** Dates as the reader sees them: in Spanish and in the business timezone, whatever the browser's. */
const TIME_ZONE = "Europe/Madrid";
const LOCALE = "es-ES";

const MINUTE = 60_000;
const HOUR = 60 * MINUTE;
const DAY = 24 * HOUR;

const dayMonth = new Intl.DateTimeFormat(LOCALE, {
  timeZone: TIME_ZONE,
  day: "numeric",
  month: "short",
});
const dayMonthYear = new Intl.DateTimeFormat(LOCALE, {
  timeZone: TIME_ZONE,
  day: "numeric",
  month: "short",
  year: "numeric",
});
const time = new Intl.DateTimeFormat(LOCALE, {
  timeZone: TIME_ZONE,
  hour: "2-digit",
  minute: "2-digit",
});
const fullDate = new Intl.DateTimeFormat(LOCALE, {
  timeZone: TIME_ZONE,
  day: "numeric",
  month: "long",
  year: "numeric",
  hour: "2-digit",
  minute: "2-digit",
});
const longDay = new Intl.DateTimeFormat(LOCALE, {
  timeZone: TIME_ZONE,
  weekday: "long",
  day: "numeric",
  month: "long",
  year: "numeric",
});
const calendarDate = new Intl.DateTimeFormat("en-CA", {
  timeZone: TIME_ZONE,
  year: "numeric",
  month: "2-digit",
  day: "2-digit",
});

/** *ahora*, *hace 14 min* or *hace 2 h* within a day; then the day, with the year when not this one. */
export function formatRelative(iso: string, now: Date = new Date()): string {
  const date = new Date(iso);
  const elapsed = now.getTime() - date.getTime();
  if (elapsed < MINUTE) {
    return "ahora";
  }
  if (elapsed < HOUR) {
    return `hace ${Math.floor(elapsed / MINUTE)} min`;
  }
  if (elapsed < DAY) {
    return `hace ${Math.floor(elapsed / HOUR)} h`;
  }
  return formatDay(date, now);
}

/** The time of the browse list, with *Hoy*, *Ayer* or the day, by the calendar of Madrid. */
export function formatTimeColumn(
  iso: string,
  now: Date = new Date(),
): { time: string; day: string } {
  const date = new Date(iso);
  const daysAgo = dayNumber(now) - dayNumber(date);
  const day = daysAgo === 0 ? "Hoy" : daysAgo === 1 ? "Ayer" : formatDay(date, now);
  return { time: time.format(date), day };
}

export function formatFullDate(iso: string): string {
  return fullDate.format(new Date(iso));
}

export function formatToday(now: Date = new Date()): string {
  return longDay.format(now);
}

function formatDay(date: Date, now: Date): string {
  const sameYear = calendarDate.format(date).slice(0, 4) === calendarDate.format(now).slice(0, 4);
  return (sameYear ? dayMonth : dayMonthYear).format(date);
}

/** Days since the epoch of the date's calendar day in Madrid, so consecutive days differ by 1. */
function dayNumber(date: Date): number {
  return Date.parse(`${calendarDate.format(date)}T00:00:00Z`) / DAY;
}
