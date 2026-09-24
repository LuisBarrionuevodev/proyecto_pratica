import type { MRT_PaginationState, MRT_SortingState } from "material-react-table";

import { DEFAULT_BANDEJA_CLIENT_PAGE_SIZE } from "../../../utils/buildClientPaginationSummary";
import type { OperativaPendientesTab } from "./operativaComprobacionBaseCache";
import {
  EMPTY_OPERATIVA_FILTRO_INPUTS,
  type OperativaComprobacionFiltroInputs,
  type OperativaComprobacionFiltroPayload,
} from "./buildOperativaComprobacionFiltroPayload";
import { isOperativeComprobacionTab } from "./operativaComprobacionTabChange";

export type OperativaTabFiltroMemory = {
  inputs: OperativaComprobacionFiltroInputs;
  applied: OperativaComprobacionFiltroPayload | null;
};

export type OperativaTabTableMemory = {
  pagination: MRT_PaginationState;
  sorting: MRT_SortingState;
};

export type OperativaTabMemory = {
  filtro: OperativaTabFiltroMemory;
  table: OperativaTabTableMemory;
};

export type OperativaMemoryByTab = Record<OperativaPendientesTab, OperativaTabMemory>;

/** Estado de tabla operativa por bandeja (paginación + sort). */
export function createDefaultOperativaTabTableMemory(): OperativaTabTableMemory {
  return {
    pagination: { pageIndex: 0, pageSize: DEFAULT_BANDEJA_CLIENT_PAGE_SIZE },
    sorting: [],
  };
}

/** Filtros operativos por bandeja (inputs visibles + payload aplicado). */
export function createDefaultOperativaTabFiltroMemory(): OperativaTabFiltroMemory {
  return {
    inputs: { ...EMPTY_OPERATIVA_FILTRO_INPUTS },
    applied: null,
  };
}

/** Memoria inicial vacía para las tres bandejas operativas. */
export function createOperativaMemoryByTab(): OperativaMemoryByTab {
  return {
    expediente: {
      filtro: createDefaultOperativaTabFiltroMemory(),
      table: createDefaultOperativaTabTableMemory(),
    },
    oficio: {
      filtro: createDefaultOperativaTabFiltroMemory(),
      table: createDefaultOperativaTabTableMemory(),
    },
    reinspeccion: {
      filtro: createDefaultOperativaTabFiltroMemory(),
      table: createDefaultOperativaTabTableMemory(),
    },
  };
}

/** Captura inputs + payload aplicado para persistir al cambiar de tab. */
export function snapshotOperativaFiltroMemory(
  inputs: OperativaComprobacionFiltroInputs,
  applied: OperativaComprobacionFiltroPayload | null
): OperativaTabFiltroMemory {
  return {
    inputs: { ...inputs },
    applied: applied ? { ...applied } : null,
  };
}

/** Filtros activos del tab destino (sin forzar null en ensureTabLoaded). */
export function resolveOperativaTabAppliedFilters(
  tab: string,
  memoryByTab: OperativaMemoryByTab
): OperativaComprobacionFiltroPayload | null {
  if (!isOperativeComprobacionTab(tab)) return null;
  return memoryByTab[tab].filtro.applied;
}

/** Firma estable del payload aplicado para detectar dataset ya cargado en sesión. */
export function operativaFiltersSignature(
  filters: OperativaComprobacionFiltroPayload | null
): string {
  return JSON.stringify(filters ?? { __base: true });
}

/** True si hay que intercambiar memoria entre bandejas operativas (no Recorrido). */
export function shouldSwapOperativaTabMemory(
  prev: OperativaPendientesTab | string,
  next: OperativaPendientesTab | string
): boolean {
  return isOperativeComprobacionTab(prev) && isOperativeComprobacionTab(next) && prev !== next;
}
