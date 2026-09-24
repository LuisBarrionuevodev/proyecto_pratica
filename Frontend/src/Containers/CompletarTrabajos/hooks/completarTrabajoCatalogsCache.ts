import {
  fetchContraproducencias,
  fetchInspectores,
  fetchMotivos,
  fetchMotivosComprobacion,
} from "../../../api/gridApi";
import {
  fetchItemsActaInspeccionCatalog,
  type IItemActaInspeccionCatalogItem,
} from "../../../api/itemActaInspeccionCatalogApi";
import {
  fetchRubrosCatalogoCached,
  rubroItemsToNombres,
} from "../../../utils/rubrosCatalogCache";

export type CompletarTrabajoCatalogs = {
  motivos: string[];
  motivosComprobacion: string[];
  contraproducencias: string[];
  inspectores: string[];
  /** Nombres canónicos de `Rubro` (GET /grid/catalogs/rubros). */
  rubros: string[];
  itemsActaInspeccion: IItemActaInspeccionCatalogItem[];
};

let memoryCache: CompletarTrabajoCatalogs | null = null;
let inflight: Promise<CompletarTrabajoCatalogs> | null = null;

async function loadFromApi(): Promise<CompletarTrabajoCatalogs> {
  const [motivos, motivosComp, contras, insp, rubrosItems, itemsActaInspeccion] = await Promise.all([
    fetchMotivos(),
    fetchMotivosComprobacion(),
    fetchContraproducencias(),
    fetchInspectores(),
    fetchRubrosCatalogoCached(),
    fetchItemsActaInspeccionCatalog(),
  ]);
  return {
    motivos: [...new Set(motivos.items.map((i) => i.nombre))],
    motivosComprobacion: [...new Set(motivosComp.items.map((i) => i.nombre))],
    contraproducencias: [...new Set(contras.items.map((i) => i.nombre))],
    inspectores: [...new Set(insp.items.map((i) => i.nombre))],
    rubros: rubroItemsToNombres(rubrosItems),
    itemsActaInspeccion,
  };
}

/**
 * Catálogos del modal Completar trabajo: una sola carga por sesión (SPA), compartida entre montajes.
 */
export function fetchCompletarTrabajoCatalogsCached(): Promise<CompletarTrabajoCatalogs> {
  if (memoryCache) {
    return Promise.resolve({
      ...memoryCache,
      inspectores: memoryCache.inspectores ?? [],
      rubros: memoryCache.rubros ?? [],
      itemsActaInspeccion: memoryCache.itemsActaInspeccion ?? [],
    });
  }
  if (inflight) return inflight;
  inflight = loadFromApi()
    .then((data) => {
      memoryCache = data;
      inflight = null;
      return data;
    })
    .catch((e) => {
      inflight = null;
      throw e;
    });
  return inflight;
}

/** Solo tests o logout explícito si en el futuro hiciera falta. */
export function clearCompletarTrabajoCatalogsCache(): void {
  memoryCache = null;
  inflight = null;
}
