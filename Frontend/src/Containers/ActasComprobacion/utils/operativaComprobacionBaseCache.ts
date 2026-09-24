import type { IActuacionesPendientesItem } from "../../../api/actuacionesPendientesApi";
import type { IPendientesOficioItem } from "../../../api/actuacionesPendientesApi";
import type { IReinspeccionOficioPendienteRow } from "../../../api/actuacionesComprobacionActasApi";

import {
  operativaComprobacionTieneFiltro,
  type OperativaComprobacionFiltroPayload,
} from "./buildOperativaComprobacionFiltroPayload";
import type { OperativaComprobacionTabKey } from "./operativaComprobacionTabChange";

export type OperativaPendientesTab = OperativaComprobacionTabKey;

export type ExpedienteBaseSnapshot = {
  items: IActuacionesPendientesItem[];
  total: number;
};

export type OficioBaseSnapshot = {
  items: IPendientesOficioItem[];
  total: number;
};

export type ReinBaseSnapshot = {
  items: IReinspeccionOficioPendienteRow[];
  total: number;
};

export type OperativaBaseCacheState = {
  expediente: { valid: boolean; snapshot: ExpedienteBaseSnapshot | null };
  oficio: { valid: boolean; snapshot: OficioBaseSnapshot | null };
  reinspeccion: { valid: boolean; snapshot: ReinBaseSnapshot | null };
};

export type OperativaTabLoadAction = "restore-base" | "fetch";

/** Crea estado vacío de cache base (solo memoria de sesión). */
export function createOperativaBaseCacheState(): OperativaBaseCacheState {
  return {
    expediente: { valid: false, snapshot: null },
    oficio: { valid: false, snapshot: null },
    reinspeccion: { valid: false, snapshot: null },
  };
}

/** True si el tab tiene snapshot base válido sin filtros activos. */
export function hasValidOperativaBase(cache: OperativaBaseCacheState, tab: OperativaPendientesTab): boolean {
  return cache[tab].valid && cache[tab].snapshot != null;
}

/** Invalida snapshots base de los tabs indicados (p. ej. tras mutación). */
export function invalidateOperativaBaseTabs(
  cache: OperativaBaseCacheState,
  tabs: OperativaPendientesTab[]
): void {
  for (const tab of tabs) {
    cache[tab].valid = false;
    cache[tab].snapshot = null;
  }
}

/** True si la carga corresponde al dataset base (sin filtros operativos). */
export function isOperativaBaseLoad(
  tab: OperativaPendientesTab,
  filters: OperativaComprobacionFiltroPayload | null
): boolean {
  return !operativaComprobacionTieneFiltro(tab, filters);
}

/**
 * Decide si al entrar a un tab se restaura cache base o se requiere GET.
 * Las búsquedas filtradas siempre hacen fetch.
 */
export function resolveOperativaTabLoadAction(
  tab: OperativaPendientesTab,
  filters: OperativaComprobacionFiltroPayload | null,
  cache: OperativaBaseCacheState
): OperativaTabLoadAction {
  if (!isOperativaBaseLoad(tab, filters)) return "fetch";
  if (hasValidOperativaBase(cache, tab)) return "restore-base";
  return "fetch";
}
