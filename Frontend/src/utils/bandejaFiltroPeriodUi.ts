import { toIsoDateLocal } from "./dateRange";

export type BandejaPeriodMode = "month" | "range";

export const BANDEJA_MESES_OPTS = Array.from({ length: 12 }, (_, i) => ({
  value: String(i + 1),
  label: String(i + 1),
}));

export const BANDEJA_MESES_OPTS_WITH_EMPTY = [{ value: "", label: "—" }, ...BANDEJA_MESES_OPTS];

/** Opciones de año alrededor del año de referencia (mismo criterio que Notificaciones/Comprobación). */
export function bandejaYearOptions(center: number): { value: string; label: string }[] {
  const out: { value: string; label: string }[] = [{ value: "", label: "—" }];
  for (let y = center - 5; y <= center + 2; y++) {
    out.push({ value: String(y), label: String(y) });
  }
  return out;
}

/** Mes/año calendario actual para defaults de selectores. */
export function bandejaDefaultMonthYear(ref: Date = new Date()): { mes: number; anio: number } {
  return { mes: ref.getMonth() + 1, anio: ref.getFullYear() };
}

/** Convierte mes (1–12) y año a rango ISO inclusive del mes. */
export function monthYearToIsoRange(
  mes: number,
  anio: number
): { desde: string; hasta: string } {
  const first = new Date(anio, mes - 1, 1);
  const last = new Date(anio, mes, 0);
  return { desde: toIsoDateLocal(first), hasta: toIsoDateLocal(last) };
}
