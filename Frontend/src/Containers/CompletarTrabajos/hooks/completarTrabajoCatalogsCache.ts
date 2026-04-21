import {
  fetchContraproducencias,
  fetchInspectores,
  fetchMotivos,
  fetchMotivosComprobacion,
} from "../../../api/gridApi";

export type CompletarTrabajoCatalogs = {
  motivos: string[];
  motivosComprobacion: string[];
  contraproducencias: string[];
  inspectores: string[];
};

let memoryCache: CompletarTrabajoCatalogs | null = null;
let inflight: Promise<CompletarTrabajoCatalogs> | null = null;

async function loadFromApi(): Promise<CompletarTrabajoCatalogs> {
  const [motivos, motivosComp, contras, insp] = await Promise.all([
    fetchMotivos(),
    fetchMotivosComprobacion(),
    fetchContraproducencias(),
    fetchInspectores(),
  ]);
  return {
    motivos: [...new Set(motivos.items.map((i) => i.nombre))],
    motivosComprobacion: [...new Set(motivosComp.items.map((i) => i.nombre))],
    contraproducencias: [...new Set(contras.items.map((i) => i.nombre))],
    inspectores: [...new Set(insp.items.map((i) => i.nombre))],
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
