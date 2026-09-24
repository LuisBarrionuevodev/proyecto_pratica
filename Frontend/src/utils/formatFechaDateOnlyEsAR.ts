/** Fecha calendario ISO `YYYY-MM-DD` (sin hora). No usar con timestamps. */
export const DATE_ONLY_RE = /^(\d{4})-(\d{2})-(\d{2})$/;

const FALLBACK_EM_DASH = "—";

/**
 * Parsea `YYYY-MM-DD` como fecha local (medianoche local), sin interpretación UTC.
 */
export function parseDateOnlyLocal(value: string): Date | null {
  const trimmed = value.trim();
  const m = DATE_ONLY_RE.exec(trimmed);
  if (!m) return null;

  const year = Number(m[1]);
  const month = Number(m[2]);
  const day = Number(m[3]);
  if (!Number.isFinite(year) || !Number.isFinite(month) || !Number.isFinite(day)) return null;

  const localDate = new Date(year, month - 1, day);
  if (
    localDate.getFullYear() !== year ||
    localDate.getMonth() !== month - 1 ||
    localDate.getDate() !== day
  ) {
    return null;
  }
  return localDate;
}

/**
 * Formatea una fecha calendario `YYYY-MM-DD` para UI es-AR (`dateStyle: medium`).
 * Valores vacíos → ``"—"``. Timestamps u otros formatos no se parsean como date-only.
 */
export function formatFechaDateOnlyEsAR(value: string | null | undefined): string {
  if (value == null) return FALLBACK_EM_DASH;
  const trimmed = String(value).trim();
  if (!trimmed) return FALLBACK_EM_DASH;

  const localDate = parseDateOnlyLocal(trimmed);
  if (!localDate) return trimmed;

  return localDate.toLocaleDateString("es-AR", { dateStyle: "medium" });
}
