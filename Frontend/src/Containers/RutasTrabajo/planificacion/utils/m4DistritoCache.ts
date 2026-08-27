import type { IRutaIniciadorPendienteRow } from "../../../../api/rutasTrabajoApi";
import type { IRutaPoolDiaRow } from "../../../../api/rutaPoolDiaApi";

/** Chunk M4 por request (debe coincidir con usePlanificacionController). */
export const M4_PAGE_MAP_CHUNK = 500;

/** Tope de páginas M4 consecutivas (debe coincidir con usePlanificacionController). */
export const M4_MAP_MAX_PAGES = 40;

/** Presupuesto máximo de filas cacheadas en conjunto (no por entrada). */
export const M4_DISTRICT_CACHE_MAX_TOTAL_ROWS = M4_PAGE_MAP_CHUNK * M4_MAP_MAX_PAGES;

/** Máximo de distritos distintos en LRU. */
export const M4_DISTRICT_CACHE_MAX_ENTRIES = 5;

export interface M4DistritoCacheEntry {
  rows: IRutaIniciadorPendienteRow[];
  totalReported: number;
  fetchedAt: number;
}

/**
 * LRU acotado por cantidad de distritos y filas totales.
 * `Map` preserva orden de inserción: frente = LRU, final = MRU.
 */
export class M4DistritoCache {
  private readonly entries = new Map<number, M4DistritoCacheEntry>();

  get(distritoId: number): M4DistritoCacheEntry | undefined {
    const entry = this.entries.get(distritoId);
    if (!entry) return undefined;
    this.entries.delete(distritoId);
    this.entries.set(distritoId, entry);
    return entry;
  }

  set(distritoId: number, entry: M4DistritoCacheEntry): void {
    if (this.entries.has(distritoId)) {
      this.entries.delete(distritoId);
    }
    this.entries.set(distritoId, entry);
    this.enforceLimits(distritoId);
  }

  delete(distritoId: number): void {
    this.entries.delete(distritoId);
  }

  clear(): void {
    this.entries.clear();
  }

  size(): number {
    return this.entries.size;
  }

  totalRows(): number {
    let sum = 0;
    for (const entry of this.entries.values()) {
      sum += entry.rows.length;
    }
    return sum;
  }

  has(distritoId: number): boolean {
    return this.entries.has(distritoId);
  }

  private enforceLimits(protectedDistritoId: number): void {
    while (
      this.entries.size > M4_DISTRICT_CACHE_MAX_ENTRIES ||
      this.totalRows() > M4_DISTRICT_CACHE_MAX_TOTAL_ROWS
    ) {
      const victim = [...this.entries.keys()].find((id) => id !== protectedDistritoId);
      if (victim === undefined) break;
      this.entries.delete(victim);
    }
  }
}

function poolIniciadorIdFromRow(row: IRutaPoolDiaRow): number | null {
  const id = Number(row.iniciador_id ?? row.iniciador_ruta_id);
  return Number.isFinite(id) && id > 0 ? id : null;
}

/**
 * Invalida cache M4 al quitar ítems del pool (OPER-RUTA.FUNCIONAL-2B.1).
 * Usa snapshot previo del pool para resolver `distrito_id`.
 */
export function invalidateM4CacheOnPoolRemoval(
  cache: M4DistritoCache,
  prevIniciadorIds: readonly number[],
  nextIniciadorIds: readonly number[],
  prevPoolRowsByIniciadorId: Readonly<Record<number, IRutaPoolDiaRow>>
): void {
  const nextSet = new Set(nextIniciadorIds);
  const removed = prevIniciadorIds.filter((id) => !nextSet.has(id));
  if (removed.length === 0) return;

  let needsFullClear = false;
  for (const iniciadorId of removed) {
    const poolRow = prevPoolRowsByIniciadorId[iniciadorId];
    const distritoId = poolRow?.distrito_id;
    if (distritoId != null && Number.isFinite(Number(distritoId))) {
      cache.delete(Number(distritoId));
    } else {
      needsFullClear = true;
      break;
    }
  }
  if (needsFullClear) {
    cache.clear();
  }
}

/** Construye mapa iniciadorId → fila pool para snapshot de invalidación. */
export function buildPoolRowsByIniciadorId(
  poolBackendItems: readonly IRutaPoolDiaRow[]
): Record<number, IRutaPoolDiaRow> {
  const out: Record<number, IRutaPoolDiaRow> = {};
  for (const row of poolBackendItems) {
    const id = poolIniciadorIdFromRow(row);
    if (id != null) out[id] = row;
  }
  return out;
}
