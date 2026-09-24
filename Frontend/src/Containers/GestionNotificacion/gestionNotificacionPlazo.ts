import type { IActuacionesPendientesItem } from "../../api/actuacionesPendientesApi";

/** En plazo: más de 4 días hábiles hasta vencimiento → d >= 5 */
export const DIAS_EN_PLAZO_MIN = 5;

/** Por vencer: entre 1 y 4 días hábiles (inclusive). Incluye el tramo intermedio 3–4. */
export const POR_VENCER_MIN = 1;
export const POR_VENCER_MAX = 4;

export type PlazoOperativoSlice = "total" | "en_plazo" | "por_vencer" | "vencidas_o_hoy";

/** Slices operativos servidos por ``pendientes/expediente`` con ``plazo_slice``. */
export type OperativePlazoExpedienteSlice = "en_plazo" | "por_vencer";

/**
 * Clasificación por `dias_restantes` del backend (derivado de `Notificacion.fecha_vencimiento`).
 * Nota: el API devuelve 0 tanto si el plazo venció como si vence hoy.
 * Días 1–4 van a **Por vencer**; desde 5 a **En plazo**.
 * La tab **Pendiente reinspección** (`vencidas_o_hoy`) usa `/actuaciones/pendientes-notificacion`, no este filtro.
 * El tab **Historial** lista por período documental (filtro aparte).
 */
export function sliceLabel(slice: PlazoOperativoSlice): string {
  switch (slice) {
    case "total":
      return "Historial de notificaciones";
    case "en_plazo":
      return "En plazo";
    case "por_vencer":
      return "Por vencer";
    case "vencidas_o_hoy":
      return "Pendiente reinspección";
    default:
      return slice;
  }
}

export function matchesPlazoSlice(row: IActuacionesPendientesItem, slice: PlazoOperativoSlice): boolean {
  if (row.source_type !== "NOTIFICACION") return false;
  if (slice === "vencidas_o_hoy") return false;
  const d = row.dias_restantes;
  if (slice === "total") return true;
  if (d === null || d === undefined) return false;
  if (slice === "en_plazo") return d >= DIAS_EN_PLAZO_MIN;
  if (slice === "por_vencer") return d >= POR_VENCER_MIN && d <= POR_VENCER_MAX;
  return true;
}

export function countByPlazoSlice(
  rows: IActuacionesPendientesItem[],
  pendienteReinspeccionCount = 0
): Record<PlazoOperativoSlice, number> {
  const noti = rows.filter((r) => r.source_type === "NOTIFICACION");
  return {
    total: noti.length,
    en_plazo: noti.filter((r) => matchesPlazoSlice(r, "en_plazo")).length,
    por_vencer: noti.filter((r) => matchesPlazoSlice(r, "por_vencer")).length,
    vencidas_o_hoy: pendienteReinspeccionCount,
  };
}

export type OperativePlazoSliceLoadState = Record<OperativePlazoExpedienteSlice, boolean>;

/** Indica si hace falta pedir ``pendientes/expediente`` para un slice operativo. */
export function operativePlazoSliceShouldFetch(
  slice: OperativePlazoExpedienteSlice,
  loaded: OperativePlazoSliceLoadState,
  force = false
): boolean {
  return force || !loaded[slice];
}

/** Slice operativo complementario a invalidar tras mutación en el activo. */
export function operativePlazoSlicePeerToInvalidate(
  active: OperativePlazoExpedienteSlice
): OperativePlazoExpedienteSlice {
  return active === "en_plazo" ? "por_vencer" : "en_plazo";
}
