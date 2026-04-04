import type { IActuacionesPendientesItem } from "../../api/actuacionesPendientesApi";

/** En plazo: más de 4 días → d >= 5 */
export const DIAS_EN_PLAZO_MIN = 5;

/** Por vencer: entre 1 y 2 días (inclusive). */
export const POR_VENCER_MIN = 1;
export const POR_VENCER_MAX = 2;

export type PlazoOperativoSlice = "total" | "en_plazo" | "por_vencer" | "vencidas_o_hoy";

/**
 * Clasificación por `dias_restantes` del backend (derivado de `Notificacion.fecha_vencimiento`).
 * Nota: el API devuelve 0 tanto si el plazo venció como si vence hoy.
 * Días 3 y 4 no entran en "En plazo" (>4) ni en "Por vencer" (1–2): solo se ven al elegir **Total**.
 */
export function sliceLabel(slice: PlazoOperativoSlice): string {
  switch (slice) {
    case "total":
      return "Total";
    case "en_plazo":
      return "En plazo";
    case "por_vencer":
      return "Por vencer";
    case "vencidas_o_hoy":
      return "Vencidas o hoy";
    default:
      return slice;
  }
}

export function matchesPlazoSlice(row: IActuacionesPendientesItem, slice: PlazoOperativoSlice): boolean {
  if (row.source_type !== "NOTIFICACION") return false;
  const d = row.dias_restantes;
  if (slice === "total") return true;
  if (d === null || d === undefined) return false;
  if (slice === "en_plazo") return d >= DIAS_EN_PLAZO_MIN;
  if (slice === "por_vencer") return d >= POR_VENCER_MIN && d <= POR_VENCER_MAX;
  if (slice === "vencidas_o_hoy") return d === 0;
  return true;
}

export function countByPlazoSlice(
  rows: IActuacionesPendientesItem[]
): Record<PlazoOperativoSlice, number> {
  const noti = rows.filter((r) => r.source_type === "NOTIFICACION");
  return {
    total: noti.length,
    en_plazo: noti.filter((r) => matchesPlazoSlice(r, "en_plazo")).length,
    por_vencer: noti.filter((r) => matchesPlazoSlice(r, "por_vencer")).length,
    vencidas_o_hoy: noti.filter((r) => matchesPlazoSlice(r, "vencidas_o_hoy")).length,
  };
}
