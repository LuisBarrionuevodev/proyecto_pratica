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

export function resolveRelevadorIdsFromNombres(
  nombres: string[],
  catalog: { id: number; nombre: string }[]
): number[] {
  const byNorm = new Map(
    catalog.map((c) => [c.nombre.trim().toUpperCase(), c.id] as const)
  );
  const ids: number[] = [];
  const seen = new Set<number>();
  for (const nombre of nombres) {
    const id = byNorm.get(nombre.trim().toUpperCase());
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
