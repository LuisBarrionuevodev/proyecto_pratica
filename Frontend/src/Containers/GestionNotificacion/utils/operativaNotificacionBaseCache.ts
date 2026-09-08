import type { IActuacionesPendientesItem } from "../../../api/actuacionesPendientesApi";

import {
  operativaNotificacionTieneFiltro,
  type OperativaNotificacionFiltroPayload,
} from "./buildOperativaNotificacionFiltroPayload";

export type OperativaNotificacionSlice = "en_plazo" | "por_vencer" | "reinspeccion";

export type PlazoBaseSnapshot = {
  items: IActuacionesPendientesItem[];
  total: number;
};

export type ReinspeccionBaseSnapshot = {
  items: IActuacionesPendientesItem[];
  total: number;
};

export type OperativaNotificacionBaseCacheState = {
  en_plazo: { valid: boolean; snapshot: PlazoBaseSnapshot | null };
  por_vencer: { valid: boolean; snapshot: PlazoBaseSnapshot | null };
  reinspeccion: { valid: boolean; snapshot: ReinspeccionBaseSnapshot | null };
};

export type OperativaTabLoadAction = "restore-base" | "fetch";

/** Crea estado vacío de cache base (solo memoria de sesión). */
export function createOperativaNotificacionBaseCacheState(): OperativaNotificacionBaseCacheState {
  return {
    en_plazo: { valid: false, snapshot: null },
    por_vencer: { valid: false, snapshot: null },
    reinspeccion: { valid: false, snapshot: null },
  };
}

/** True si el slice tiene snapshot base válido. */
export function hasValidOperativaNotificacionBase(
  cache: OperativaNotificacionBaseCacheState,
  slice: OperativaNotificacionSlice
): boolean {
  return cache[slice].valid && cache[slice].snapshot != null;
}

/** Invalida snapshots base de los slices indicados (p. ej. tras mutación). */
export function invalidateOperativaNotificacionBaseTabs(
  cache: OperativaNotificacionBaseCacheState,
  slices: OperativaNotificacionSlice[]
): void {
  for (const slice of slices) {
    cache[slice].valid = false;
    cache[slice].snapshot = null;
  }
}

/** True si la carga corresponde al dataset base (sin filtros operativos). */
export function isOperativaNotificacionBaseLoad(filters: OperativaNotificacionFiltroPayload | null): boolean {
  if (!filters) return true;
  return !operativaNotificacionTieneFiltro(filters);
}

/**
 * Decide si al entrar a un slice se restaura cache base o se requiere GET.
 * Las búsquedas filtradas siempre hacen fetch.
 */
export function resolveOperativaNotificacionTabLoadAction(
  slice: OperativaNotificacionSlice,
  filters: OperativaNotificacionFiltroPayload | null,
  cache: OperativaNotificacionBaseCacheState
): OperativaTabLoadAction {
  if (!isOperativaNotificacionBaseLoad(filters)) return "fetch";
  if (hasValidOperativaNotificacionBase(cache, slice)) return "restore-base";
  return "fetch";
}
