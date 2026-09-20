import type { IRutaIniciadorPendienteRow } from "../../../../api/rutasTrabajoApi";
import type { IRutaPoolDiaRow } from "../../../../api/rutaPoolDiaApi";

export type M4PoolInvalidationContext = {
  distritoIds: Set<number>;
  invalidateOutside: boolean;
};

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
 * Resuelve distrito efectivo de un ítem pool (FK, fila iniciador o domicilio anidado).
 */
export function resolveEffectiveDistritoIdFromPoolRow(
  poolRow: IRutaPoolDiaRow,
  iniciadorRow?: IRutaIniciadorPendienteRow | null
): number | null {
  const top = poolRow.distrito_id;
  if (typeof top === "number" && Number.isFinite(top)) return top;
  const fromIniciador = iniciadorRow?.distrito_id ?? iniciadorRow?.domicilio?.distrito_id ?? null;
  if (typeof fromIniciador === "number" && Number.isFinite(fromIniciador)) return fromIniciador;
  return null;
}

/**
 * Calcula qué contextos M4 invalidar al quitar ítems del pool.
 * Sin distrito resoluble: solo outside (no `cache.clear()` global).
 */
export function computeM4InvalidationOnPoolRemoval(
  prevIniciadorIds: readonly number[],
  nextIniciadorIds: readonly number[],
  prevPoolRowsByIniciadorId: Readonly<Record<number, IRutaPoolDiaRow>>,
  iniciadorRowsById?: Readonly<Record<number, IRutaIniciadorPendienteRow>>
): M4PoolInvalidationContext {
  const nextSet = new Set(nextIniciadorIds);
  const removed = prevIniciadorIds.filter((id) => !nextSet.has(id));
  const distritoIds = new Set<number>();
  let invalidateOutside = false;

  for (const iniciadorId of removed) {
    const poolRow = prevPoolRowsByIniciadorId[iniciadorId];
    if (!poolRow) {
      invalidateOutside = true;
      continue;
    }
    const distritoId = resolveEffectiveDistritoIdFromPoolRow(poolRow, iniciadorRowsById?.[iniciadorId]);
    if (distritoId != null) {
      distritoIds.add(distritoId);
    } else {
      invalidateOutside = true;
    }
  }

  return { distritoIds, invalidateOutside };
}

/** Aplica invalidación parcial sobre cache distrito y/o outside. */
export function applyM4InvalidationOnPoolRemoval(
  cache: M4DistritoCache,
  outsideCacheRef: { current: M4DistritoCacheEntry | null } | null,
  ctx: M4PoolInvalidationContext
): void {
  if (ctx.distritoIds.size === 0 && !ctx.invalidateOutside) return;
  for (const distritoId of ctx.distritoIds) {
    cache.delete(distritoId);
  }
  if (ctx.invalidateOutside && outsideCacheRef) {
    outsideCacheRef.current = null;
  }
}

/**
 * Invalida cache M4 al quitar ítems del pool (OPER-RUTA.FUNCIONAL-2B.1 / RUTA-UX-CIERRE.1).
 */
export function invalidateM4CacheOnPoolRemoval(
  cache: M4DistritoCache,
  prevIniciadorIds: readonly number[],
  nextIniciadorIds: readonly number[],
  prevPoolRowsByIniciadorId: Readonly<Record<number, IRutaPoolDiaRow>>,
  opts?: {
    outsideCacheRef?: { current: M4DistritoCacheEntry | null };
    iniciadorRowsById?: Readonly<Record<number, IRutaIniciadorPendienteRow>>;
  }
): void {
  const ctx = computeM4InvalidationOnPoolRemoval(
    prevIniciadorIds,
    nextIniciadorIds,
    prevPoolRowsByIniciadorId,
    opts?.iniciadorRowsById
  );
  applyM4InvalidationOnPoolRemoval(cache, opts?.outsideCacheRef ?? null, ctx);
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
