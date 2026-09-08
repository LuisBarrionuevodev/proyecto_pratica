export type OperativaComprobacionTabKey = "expediente" | "oficio" | "reinspeccion";

const OPERATIVE_TABS = new Set<OperativaComprobacionTabKey>(["expediente", "oficio", "reinspeccion"]);

/** True si el tab corresponde a una bandeja operativa (no Recorrido). */
export function isOperativeComprobacionTab(tab: string): tab is OperativaComprobacionTabKey {
  return OPERATIVE_TABS.has(tab as OperativaComprobacionTabKey);
}

/**
 * Al cambiar entre tabs operativos se deben limpiar todos los filtros visibles
 * para no heredar criterios del tab anterior.
 */
export function shouldResetOperativaFiltroOnTabChange(
  prev: OperativaComprobacionTabKey | string,
  next: OperativaComprobacionTabKey | string
): boolean {
  return isOperativeComprobacionTab(prev) && isOperativeComprobacionTab(next) && prev !== next;
}
