import { describe, expect, it } from "vitest";

import type { IRutaIniciadorPendienteRow } from "../../../../api/rutasTrabajoApi";
import type { IRutaPoolDiaRow } from "../../../../api/rutaPoolDiaApi";
import {
  M4_DISTRICT_CACHE_MAX_ENTRIES,
  M4_DISTRICT_CACHE_MAX_TOTAL_ROWS,
  M4DistritoCache,
  type M4DistritoCacheEntry,
  buildPoolRowsByIniciadorId,
  invalidateM4CacheOnPoolRemoval,
} from "./m4DistritoCache";

function row(id: number): IRutaIniciadorPendienteRow {
  return { id, tipo_iniciador: "RELEVAMIENTO" } as IRutaIniciadorPendienteRow;
}

function entry(rows: IRutaIniciadorPendienteRow[], totalReported?: number): M4DistritoCacheEntry {
  return { rows, totalReported: totalReported ?? rows.length, fetchedAt: Date.now() };
}

function poolRow(iniciadorId: number, distritoId: number | null): IRutaPoolDiaRow {
  return {
    pool_id: iniciadorId,
    fecha: "2026-08-01",
    estado: "EN_POOL",
    iniciador_id: iniciadorId,
    iniciador_ruta_id: iniciadorId,
    distrito_id: distritoId,
  } as IRutaPoolDiaRow;
}

describe("M4DistritoCache — LRU y límites", () => {
  it("LRU básico: get mueve entrada a MRU", () => {
    const cache = new M4DistritoCache();
    cache.set(10, entry([row(1)]));
    cache.set(5, entry([row(2)]));
    expect(cache.has(10)).toBe(true);
    cache.get(10);
    cache.set(7, entry([row(3)]));
    cache.set(8, entry([row(4)]));
    cache.set(9, entry([row(5)]));
    cache.set(11, entry([row(6)]));
    expect(cache.has(10)).toBe(true);
    expect(cache.has(5)).toBe(false);
  });

  it("máximo 5 entradas: la 6ª expulsa LRU", () => {
    const cache = new M4DistritoCache();
    for (let d = 1; d <= M4_DISTRICT_CACHE_MAX_ENTRIES + 1; d += 1) {
      cache.set(d, entry([row(d)]));
    }
    expect(cache.size()).toBe(M4_DISTRICT_CACHE_MAX_ENTRIES);
    expect(cache.has(1)).toBe(false);
    expect(cache.has(M4_DISTRICT_CACHE_MAX_ENTRIES + 1)).toBe(true);
  });

  it("presupuesto de filas: expulsa LRU hasta cumplir tope", () => {
    const cache = new M4DistritoCache();
    const half = Math.floor(M4_DISTRICT_CACHE_MAX_TOTAL_ROWS / 2);
    cache.set(1, entry(Array.from({ length: half }, (_, i) => row(i + 1)), half));
    cache.set(2, entry(Array.from({ length: half }, (_, i) => row(i + half + 1)), half));
    expect(cache.totalRows()).toBe(half * 2);
    cache.set(3, entry([row(999)]));
    expect(cache.has(1)).toBe(false);
    expect(cache.has(2)).toBe(true);
    expect(cache.has(3)).toBe(true);
    expect(cache.totalRows()).toBeLessThanOrEqual(M4_DISTRICT_CACHE_MAX_TOTAL_ROWS);
  });

  it("replace: set mismo distrito no duplica entrada", () => {
    const cache = new M4DistritoCache();
    cache.set(10, entry([row(1)]));
    cache.set(10, entry([row(1), row(2)], 2));
    expect(cache.size()).toBe(1);
    expect(cache.get(10)?.rows).toHaveLength(2);
  });

  it("delete elimina solo el distrito indicado", () => {
    const cache = new M4DistritoCache();
    cache.set(10, entry([row(1)]));
    cache.set(5, entry([row(2)]));
    cache.delete(10);
    expect(cache.has(10)).toBe(false);
    expect(cache.has(5)).toBe(true);
  });

  it("clear vacía todo", () => {
    const cache = new M4DistritoCache();
    cache.set(10, entry([row(1)]));
    cache.set(5, entry([row(2)]));
    cache.clear();
    expect(cache.size()).toBe(0);
    expect(cache.totalRows()).toBe(0);
  });

  it("mantiene entrada recién cargada aunque ocupe todo el presupuesto", () => {
    const cache = new M4DistritoCache();
    const big = Array.from({ length: M4_DISTRICT_CACHE_MAX_TOTAL_ROWS }, (_, i) => row(i + 1));
    cache.set(99, entry(big, M4_DISTRICT_CACHE_MAX_TOTAL_ROWS));
    expect(cache.has(99)).toBe(true);
    expect(cache.totalRows()).toBe(M4_DISTRICT_CACHE_MAX_TOTAL_ROWS);
  });
});

describe("invalidateM4CacheOnPoolRemoval", () => {
  it("agregar al pool no invalida", () => {
    const cache = new M4DistritoCache();
    cache.set(10, entry([row(1)]));
    invalidateM4CacheOnPoolRemoval(cache, [1], [1, 2], { 1: poolRow(1, 10) });
    expect(cache.has(10)).toBe(true);
  });

  it("quitar pool invalida distrito resoluble", () => {
    const cache = new M4DistritoCache();
    cache.set(10, entry([row(1)]));
    cache.set(5, entry([row(2)]));
    invalidateM4CacheOnPoolRemoval(cache, [1, 2], [2], { 1: poolRow(1, 10), 2: poolRow(2, 5) });
    expect(cache.has(10)).toBe(false);
    expect(cache.has(5)).toBe(true);
  });

  it("quitar pool sin distrito resoluble limpia toda la cache", () => {
    const cache = new M4DistritoCache();
    cache.set(10, entry([row(1)]));
    invalidateM4CacheOnPoolRemoval(cache, [1], [], { 1: poolRow(1, null) });
    expect(cache.size()).toBe(0);
  });

  it("buildPoolRowsByIniciadorId indexa por iniciador", () => {
    const map = buildPoolRowsByIniciadorId([poolRow(42, 10)]);
    expect(map[42]?.distrito_id).toBe(10);
  });
});
