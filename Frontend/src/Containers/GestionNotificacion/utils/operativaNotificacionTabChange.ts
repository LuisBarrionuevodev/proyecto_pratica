import type { PlazoOperativoSlice } from "../gestionNotificacionPlazo";

const OPERATIVE_TABS = new Set<PlazoOperativoSlice>(["en_plazo", "por_vencer", "vencidas_o_hoy"]);

/** True si el slice corresponde a una bandeja operativa (no Historial). */
export function isOperativeNotificacionTab(slice: PlazoOperativoSlice): boolean {
  return OPERATIVE_TABS.has(slice);
}

/**
 * Al cambiar entre tabs operativos se deben limpiar Nº notificación y Calle
 * para no heredar filtros del tab anterior.
 */
export function shouldResetOperativaFiltroOnTabChange(
  prev: PlazoOperativoSlice,
  next: PlazoOperativoSlice
): boolean {
  return isOperativeNotificacionTab(prev) && isOperativeNotificacionTab(next) && prev !== next;
}
