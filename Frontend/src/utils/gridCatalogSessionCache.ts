import type { CatalogResponse } from "../api/gridApi";

type Entry = {
  data: CatalogResponse | null;
  inflight: Promise<CatalogResponse> | null;
};

const entries = new Map<string, Entry>();

function getEntry(key: string): Entry {
  let entry = entries.get(key);
  if (!entry) {
    entry = { data: null, inflight: null };
    entries.set(key, entry);
  }
  return entry;
}

/**
 * Una request por catálogo de grid y sesión SPA (deduplica consumidores simultáneos).
 */
export function fetchGridCatalogSessionCached(
  cacheKey: string,
  load: () => Promise<CatalogResponse>
): Promise<CatalogResponse> {
  const entry = getEntry(cacheKey);
  if (entry.data) {
    return Promise.resolve(entry.data);
  }
  if (entry.inflight) {
    return entry.inflight;
  }
  entry.inflight = load()
    .then((data) => {
      entry.data = data;
      entry.inflight = null;
      return data;
    })
    .catch((err) => {
      entry.inflight = null;
      throw err;
    });
  return entry.inflight;
}

/** Limpia un catálogo en memoria. */
export function clearGridCatalogSessionCacheKey(cacheKey: string): void {
  entries.delete(cacheKey);
}

/** Limpia catálogos en memoria (logout / 401). */
export function clearGridCatalogSessionCaches(): void {
  entries.clear();
}
