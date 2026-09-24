import type { CatalogItem } from "../api/gridApi";

/**
 * Filtra ítems de catálogo por nombre o legajo (case-insensitive).
 */
export function filterCatalogItemsByQuery(items: CatalogItem[], query: string): CatalogItem[] {
  const q = query.trim().toLowerCase();
  if (!q) return items;
  return items.filter((item) => {
    const nombre = (item.nombre ?? "").toLowerCase();
    const legajo = String(item.legajo ?? "").toLowerCase();
    return nombre.includes(q) || legajo.includes(q);
  });
}
