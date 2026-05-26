import { toIsoDateLocal } from "./dateRange";
import type { ExportDateRange, ExportPeriodMode } from "../ui/exportDataDialog.types";

export type { ExportDateRange, ExportPeriodMode };

const ISO_DATE_RE = /^\d{4}-\d{2}-\d{2}$/;

export type ResolveExportPeriodResult =
  | { ok: true; range: ExportDateRange }
  | { ok: false; error: string };

export type ValidateCustomRangeResult =
  | { ok: true }
  | { ok: false; desdeError?: string; hastaError?: string; error?: string };

/**
 * Etiqueta legible del modo de período (UI del modal de exportación).
 */
export function exportPeriodModeLabel(mode: ExportPeriodMode): string {
  switch (mode) {
    case "workweek":
      return "Semana actual (lun.–vie.)";
    case "month":
      return "Mes actual";
    case "custom":
      return "Rango personalizado";
    default:
      return mode;
  }
}

/**
 * Lunes de la semana calendario que contiene `ref` (fecha local).
 */
export function startOfWorkweekMonday(ref: Date = new Date()): Date {
  const d = new Date(ref.getFullYear(), ref.getMonth(), ref.getDate());
  const day = d.getDay();
  const daysSinceMonday = (day + 6) % 7;
  d.setDate(d.getDate() - daysSinceMonday);
  return d;
}

/**
 * Semana laboral actual: lunes a viernes de la semana calendario de `ref`.
 */
export function getWorkweekRange(ref: Date = new Date()): ExportDateRange {
  const monday = startOfWorkweekMonday(ref);
  const friday = new Date(monday);
  friday.setDate(friday.getDate() + 4);
  return {
    desde: toIsoDateLocal(monday),
    hasta: toIsoDateLocal(friday),
  };
}

/**
 * Mes calendario de `ref`: del primer al último día inclusive.
 */
export function getMonthRange(ref: Date = new Date()): ExportDateRange {
  const firstDay = new Date(ref.getFullYear(), ref.getMonth(), 1);
  const lastDay = new Date(ref.getFullYear(), ref.getMonth() + 1, 0);
  return {
    desde: toIsoDateLocal(firstDay),
    hasta: toIsoDateLocal(lastDay),
  };
}

function parseIsoDateLocal(iso: string): Date | null {
  if (!ISO_DATE_RE.test(iso)) return null;
  const [y, m, d] = iso.split("-").map(Number);
  if (!Number.isFinite(y) || !Number.isFinite(m) || !Number.isFinite(d)) return null;
  const date = new Date(y, m - 1, d);
  if (date.getFullYear() !== y || date.getMonth() !== m - 1 || date.getDate() !== d) return null;
  return date;
}

function isWithinBounds(iso: string, minDate?: string, maxDate?: string): string | null {
  if (minDate && iso < minDate) {
    return `La fecha no puede ser anterior a ${minDate}.`;
  }
  if (maxDate && iso > maxDate) {
    return `La fecha no puede ser posterior a ${maxDate}.`;
  }
  return null;
}

/**
 * Valida un rango personalizado `desde`/`hasta` (YYYY-MM-DD local).
 */
export function validateCustomExportRange(
  desde: string,
  hasta: string,
  minDate?: string,
  maxDate?: string
): ValidateCustomRangeResult {
  const desdeTrim = desde.trim();
  const hastaTrim = hasta.trim();

  if (!desdeTrim) {
    return { ok: false, desdeError: "Indicá la fecha desde.", error: "Completá la fecha desde." };
  }
  if (!hastaTrim) {
    return { ok: false, hastaError: "Indicá la fecha hasta.", error: "Completá la fecha hasta." };
  }

  if (!parseIsoDateLocal(desdeTrim)) {
    return { ok: false, desdeError: "Fecha desde inválida.", error: "Fecha desde inválida." };
  }
  if (!parseIsoDateLocal(hastaTrim)) {
    return { ok: false, hastaError: "Fecha hasta inválida.", error: "Fecha hasta inválida." };
  }

  const desdeBounds = isWithinBounds(desdeTrim, minDate, maxDate);
  if (desdeBounds) {
    return { ok: false, desdeError: desdeBounds, error: desdeBounds };
  }
  const hastaBounds = isWithinBounds(hastaTrim, minDate, maxDate);
  if (hastaBounds) {
    return { ok: false, hastaError: hastaBounds, error: hastaBounds };
  }

  if (desdeTrim > hastaTrim) {
    const msg = "La fecha desde no puede ser posterior a la fecha hasta.";
    return { ok: false, desdeError: msg, hastaError: msg, error: msg };
  }

  return { ok: true };
}

export type ResolveExportPeriodOptions = {
  customRange?: Partial<ExportDateRange>;
  minDate?: string;
  maxDate?: string;
  ref?: Date;
};

/**
 * Resuelve el rango [desde, hasta] según el modo de período del modal de exportación.
 */
export function resolveExportPeriodRange(
  mode: ExportPeriodMode,
  options: ResolveExportPeriodOptions = {}
): ResolveExportPeriodResult {
  const ref = options.ref ?? new Date();

  if (mode === "workweek") {
    const range = getWorkweekRange(ref);
    const bounded = clampRangeToBounds(range, options.minDate, options.maxDate);
    if (!bounded.ok) return bounded;
    return { ok: true, range: bounded.range };
  }

  if (mode === "month") {
    const range = getMonthRange(ref);
    const bounded = clampRangeToBounds(range, options.minDate, options.maxDate);
    if (!bounded.ok) return bounded;
    return { ok: true, range: bounded.range };
  }

  const desde = options.customRange?.desde?.trim() ?? "";
  const hasta = options.customRange?.hasta?.trim() ?? "";
  const validation = validateCustomExportRange(desde, hasta, options.minDate, options.maxDate);
  if (!validation.ok) {
    return { ok: false, error: validation.error ?? "Rango de fechas inválido." };
  }
  return { ok: true, range: { desde, hasta } };
}

function clampRangeToBounds(
  range: ExportDateRange,
  minDate?: string,
  maxDate?: string
): ResolveExportPeriodResult {
  if (minDate && range.desde < minDate) {
    return {
      ok: false,
      error: `El período seleccionado comienza antes del mínimo permitido (${minDate}).`,
    };
  }
  if (maxDate && range.hasta > maxDate) {
    return {
      ok: false,
      error: `El período seleccionado termina después del máximo permitido (${maxDate}).`,
    };
  }
  return { ok: true, range };
}

/** Formato corto para vista previa en el modal (ej. 2026-05-19 → 19/05/2026). */
export function formatExportDatePreview(iso: string): string {
  if (!ISO_DATE_RE.test(iso)) return iso;
  const [y, m, d] = iso.split("-");
  return `${d}/${m}/${y}`;
}
