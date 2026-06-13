import { fetchInspectores, type CatalogItem } from "../api/gridApi";

let memoryCache: CatalogItem[] | null = null;
let inflight: Promise<CatalogItem[]> | null = null;

/**
 * Catálogo de inspectores (ítems con id) — una carga por sesión (STAB-6).
 */
export function fetchInspectoresCatalogItemsCached(): Promise<CatalogItem[]> {
  if (memoryCache) return Promise.resolve(memoryCache);
  if (inflight) return inflight;
  inflight = fetchInspectores()
    .then((resp) => {
      const items = resp.items ?? [];
      memoryCache = items;
      inflight = null;
      return items;
    })
    .catch((e) => {
      inflight = null;
      throw e;
    });
  return inflight;
}

/** Solo tests. */
export function clearInspectoresCatalogCache(): void {
  memoryCache = null;
  inflight = null;
}
