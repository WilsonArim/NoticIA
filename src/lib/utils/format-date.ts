/**
 * Date formatting utilities for Portuguese (pt-PT) locale.
 */

const PT_LOCALE = "pt-PT";

/** Full date: "12 de março de 2026" */
export function formatFullDate(date: string | Date): string {
  const d = typeof date === "string" ? new Date(date) : date;
  return d.toLocaleDateString(PT_LOCALE, {
    day: "numeric",
    month: "long",
    year: "numeric",
  });
}

/** Short date: "12/03/2026" */
export function formatShortDate(date: string | Date): string {
  const d = typeof date === "string" ? new Date(date) : date;
  return d.toLocaleDateString(PT_LOCALE, {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  });
}

/** Date + time: "12 mar 2026, 14:30" */
export function formatDateTime(date: string | Date): string {
  const d = typeof date === "string" ? new Date(date) : date;
  return d.toLocaleDateString(PT_LOCALE, {
    day: "numeric",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

/** Relative time: "há 2 horas", "há 3 dias" */
export function formatRelativeTime(date: string | Date): string {
  const d = typeof date === "string" ? new Date(date) : date;
  const now = new Date();
  const diffMs = now.getTime() - d.getTime();
  const diffSec = Math.floor(diffMs / 1000);
  const diffMin = Math.floor(diffSec / 60);
  const diffHours = Math.floor(diffMin / 60);
  const diffDays = Math.floor(diffHours / 24);

  if (diffSec < 60) return "agora mesmo";
  if (diffMin < 60) return `há ${diffMin} min`;
  if (diffHours < 24) return `há ${diffHours}h`;
  if (diffDays < 7) return `há ${diffDays} dia${diffDays > 1 ? "s" : ""}`;
  return formatShortDate(d);
}

/** ISO date for <time> datetime attribute */
export function toISOString(date: string | Date): string {
  const d = typeof date === "string" ? new Date(date) : date;
  return d.toISOString();
}
