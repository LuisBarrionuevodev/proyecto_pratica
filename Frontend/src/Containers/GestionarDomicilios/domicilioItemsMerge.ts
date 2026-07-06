import { prioritySortKey } from "./domicilioPriorityLabels";
import type { DomiciliosSlice } from "./types";
import type { DomicilioPendienteItem } from "./types";

/** Une filas de varios slices sin duplicar domicilio_id. */
export function mergeSliceItems(
  slices: readonly DomiciliosSlice[],
  itemsBySlice: Partial<Record<DomiciliosSlice, DomicilioPendienteItem[]>>,
  filterSlice: DomiciliosSlice | "all"
): DomicilioPendienteItem[] {
  const target =
    filterSlice === "all" ? slices : slices.filter((s) => s === filterSlice);
  const seen = new Set<number>();
  const merged: DomicilioPendienteItem[] = [];

  for (const slice of target) {
    for (const item of itemsBySlice[slice] ?? []) {
      if (seen.has(item.domicilio_id)) continue;
      seen.add(item.domicilio_id);
      merged.push({ ...item, slice: item.slice ?? slice });
    }
  }
  return merged;
}

/** Ordena para revisar: menor score unificado primero (prioridad alta arriba). */
export function sortItemsForReview(items: DomicilioPendienteItem[]): DomicilioPendienteItem[] {
  return [...items].sort(
    (a, b) => prioritySortKey(a.score_unificado) - prioritySortKey(b.score_unificado)
  );
}
