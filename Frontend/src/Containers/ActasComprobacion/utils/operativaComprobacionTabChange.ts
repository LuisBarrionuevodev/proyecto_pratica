export type OperativaComprobacionTabKey = "expediente" | "oficio" | "reinspeccion";

const OPERATIVE_TABS = new Set<OperativaComprobacionTabKey>(["expediente", "oficio", "reinspeccion"]);

/** True si el tab corresponde a una bandeja operativa (no Recorrido). */
export function isOperativeComprobacionTab(tab: string): tab is OperativaComprobacionTabKey {
  return OPERATIVE_TABS.has(tab as OperativaComprobacionTabKey);
}

/**
 * True al cambiar entre bandejas operativas (expediente/oficio/reinspección).
 * La página intercambia memoria por tab en lugar de resetear filtros.
 */
export function shouldSwapOperativaTabMemory(
  prev: OperativaComprobacionTabKey | string,
  next: OperativaComprobacionTabKey | string
): boolean {
  return isOperativeComprobacionTab(prev) && isOperativeComprobacionTab(next) && prev !== next;
}

/** @deprecated Usar shouldSwapOperativaTabMemory */
export function shouldResetOperativaFiltroOnTabChange(
  prev: OperativaComprobacionTabKey | string,
  next: OperativaComprobacionTabKey | string
): boolean {
  return shouldSwapOperativaTabMemory(prev, next);
}
