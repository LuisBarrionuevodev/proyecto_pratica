import { fetchInspectores, type CatalogItem } from "../api/gridApi";
import { clearGridCatalogSessionCacheKey } from "./gridCatalogSessionCache";

const GRID_CATALOG_INSPECTORES = "/grid/catalogs/inspectores";

/**
 * Catálogo de inspectores (ítems con id) — delega en cache de sesión de `fetchInspectores`.
 */
export function fetchInspectoresCatalogItemsCached(): Promise<CatalogItem[]> {
  return fetchInspectores().then((resp) => resp.items ?? []);
}

/** Limpia solo inspectores (tests); logout usa `clearBootstrapSessionCaches`. */
export function clearInspectoresCatalogCache(): void {
  clearGridCatalogSessionCacheKey(GRID_CATALOG_INSPECTORES);
}
