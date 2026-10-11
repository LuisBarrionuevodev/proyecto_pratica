/**
 * Utilidades para celda Relevador (N:N, display coma-separado + ids para drafts).
 */

export function parseRelevadorCellValue(value: unknown): string[] {
  if (value === null || value === undefined || value === "") return [];
  if (Array.isArray(value)) {
    return value.map((v) => String(v).trim()).filter(Boolean);
  }
  const s = String(value).trim();
  if (!s) return [];
  return s.split(/[,;]/).map((p) => p.trim()).filter(Boolean);
}

export function formatRelevadorCellValue(nombres: string[]): string {
  return nombres.filter(Boolean).join(", ");
}

function relevadorNormKey(nombre: string): string {
  return nombre.trim().toUpperCase().replace(/\s+/g, " ");
}

/** Claves de lookup: etiqueta catálogo y variantes sin coma (legacy). */
function relevadorCatalogKeys(label: string): string[] {
  const norm = relevadorNormKey(label);
  const keys = new Set<string>([norm]);
  if (label.includes(",")) {
    const [ap, no] = label.split(",").map((p) => p.trim());
    if (ap && no) {
      keys.add(relevadorNormKey(`${no} ${ap}`));
      keys.add(relevadorNormKey(`${ap} ${no}`));
    }
  }
  return [...keys];
}

export function resolveRelevadorIdsFromNombres(
  nombres: string[],
  catalog: { id: number; nombre: string }[]
): number[] {
  const byNorm = new Map<string, number>();
  for (const c of catalog) {
    for (const key of relevadorCatalogKeys(c.nombre)) {
      byNorm.set(key, c.id);
    }
  }
  const ids: number[] = [];
  const seen = new Set<number>();
  for (const nombre of nombres) {
    let id: number | undefined;
    for (const key of relevadorCatalogKeys(nombre)) {
      id = byNorm.get(key);
      if (id !== undefined) break;
    }
    if (id !== undefined && !seen.has(id)) {
      seen.add(id);
      ids.push(id);
    }
  }
  return ids;
}

export function relevadorIdsToLabel(
  ids: number[],
  catalog: { id: number; nombre: string }[]
): string {
  const byId = new Map(catalog.map((c) => [c.id, c.nombre] as const));
  return ids.map((id) => byId.get(id) ?? "").filter(Boolean).join(", ");
}
