import type { IRubroCatalogItem } from "../api/rubrosCatalogApi";
import { fetchRubrosCatalogo } from "../api/rubrosCatalogApi";

let memoryCache: IRubroCatalogItem[] | null = null;
let inflight: Promise<IRubroCatalogItem[]> | null = null;

/**
 * Catálogo de rubros — una carga por sesión (STAB-8).
 */
export function fetchRubrosCatalogoCached(force = false): Promise<IRubroCatalogItem[]> {
  if (!force && memoryCache) return Promise.resolve(memoryCache);
  if (!force && inflight) return inflight;
  inflight = fetchRubrosCatalogo()
    .then((items) => {
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

/** Solo tests o refresh explícito en gestión. */
export function clearRubrosCatalogCache(): void {
  memoryCache = null;
  inflight = null;
}

/**
 * Nombres únicos ordenados para selects/autocomplete.
 */
export function rubroItemsToNombres(items: IRubroCatalogItem[]): string[] {
  return [...new Set(items.map((r) => r.nombre).filter(Boolean))].sort((a, b) =>
    a.localeCompare(b, "es", { sensitivity: "base" })
  );
}

/**
 * Incluye valor legacy si no está en catálogo (compatibilidad histórica).
 */
export function mergeLegacyRubroNames(catalogNames: string[], legacy?: string | null): string[] {
  const set = new Set(catalogNames);
  const leg = (legacy ?? "").trim();
  if (leg && !set.has(leg)) set.add(leg);
  return [...set].sort((a, b) => a.localeCompare(b, "es", { sensitivity: "base" }));
}

/**
 * Filtro local por nombre (Autocomplete).
 */
export function filterRubrosByQuery(items: IRubroCatalogItem[], query: string): IRubroCatalogItem[] {
  const q = query.trim().toLowerCase();
  if (!q) return items;
  return items.filter((r) => (r.nombre ?? "").toLowerCase().includes(q));
}

/**
 * Opciones select con legacy preservado.
 */
export function rubroSelectOptions(
  catalogNames: string[],
  legacy?: string | null
): { value: string; label: string }[] {
  const names = mergeLegacyRubroNames(catalogNames, legacy);
  return [{ value: "", label: "—" }, ...names.map((n) => ({ value: n, label: n }))];
}
