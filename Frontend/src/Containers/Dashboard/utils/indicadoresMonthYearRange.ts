import { toIsoDateLocal } from "../../../utils/dateRange";

/** Mes calendario 1–12. */
export type IndicadoresMonthSelection = {
  year: number;
  month: number;
};

export const MESES_ES: readonly string[] = [
  "Enero",
  "Febrero",
  "Marzo",
  "Abril",
  "Mayo",
  "Junio",
  "Julio",
  "Agosto",
  "Septiembre",
  "Octubre",
  "Noviembre",
  "Diciembre",
];

export function formatIndicadoresMonthYearLabel(sel: IndicadoresMonthSelection): string {
  const name = MESES_ES[sel.month - 1] ?? String(sel.month);
  return `${name} ${sel.year}`;
}

export function isFutureIndicadoresMonth(
  year: number,
  month: number,
  ref: Date = new Date()
): boolean {
  const y = ref.getFullYear();
  const m = ref.getMonth() + 1;
  if (year > y) return true;
  if (year === y && month > m) return true;
  return false;
}

/**
 * Rango inclusive del mes elegido: 1.er día → último día del mes o hoy si es el mes actual.
 */
export function monthYearToIndicadoresDateRange(
  sel: IndicadoresMonthSelection,
  ref: Date = new Date()
): { desde: string; hasta: string } {
  const desde = new Date(sel.year, sel.month - 1, 1);
  const lastDayOfMonth = new Date(sel.year, sel.month, 0);
  const today = new Date(ref.getFullYear(), ref.getMonth(), ref.getDate());
  const isCurrentMonth =
    sel.year === ref.getFullYear() && sel.month === ref.getMonth() + 1;
  const hasta = isCurrentMonth ? today : lastDayOfMonth;
  return {
    desde: toIsoDateLocal(desde),
    hasta: toIsoDateLocal(hasta),
  };
}

export function indicadoresYearOptions(ref: Date = new Date()): number[] {
  const current = ref.getFullYear();
  const start = 2020;
  const years: number[] = [];
  for (let y = current; y >= start; y -= 1) {
    years.push(y);
  }
  return years;
}
