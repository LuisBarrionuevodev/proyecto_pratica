import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { sinPool } from "./planificacion/selectors/planificacionSelectors";
import {
  M4DistritoCache,
  buildPoolRowsByIniciadorId,
  invalidateM4CacheOnPoolRemoval,
} from "./planificacion/utils/m4DistritoCache";

const root = resolve(__dirname, "../..");

function read(rel: string): string {
  return readFileSync(resolve(root, rel), "utf8");
}

describe("OPER-RUTA.FUNCIONAL-2B.1 — cache M4 por distrito", () => {
  const controllerSrc = read("Containers/RutasTrabajo/planificacion/hooks/usePlanificacionController.ts");
  const cacheSrc = read("Containers/RutasTrabajo/planificacion/utils/m4DistritoCache.ts");
  const planificacionView = read("Containers/RutasTrabajo/planificacion/PlanificacionView.tsx");
  const indexSrc = read("Containers/RutasTrabajo/index.tsx");

  it("utilidad LRU aislada con límites explícitos", () => {
    expect(cacheSrc).toContain("M4_DISTRICT_CACHE_MAX_ENTRIES = 5");
    expect(cacheSrc).toContain("M4_DISTRICT_CACHE_MAX_TOTAL_ROWS = M4_PAGE_MAP_CHUNK * M4_MAP_MAX_PAGES");
    expect(cacheSrc).toContain("class M4DistritoCache");
  });

  it("caso A — primera visita: cache miss ejecuta M4 y guarda snapshot completo", () => {
    expect(controllerSrc).toContain("const cached = cache.get(distritoId)");
    expect(controllerSrc).toContain("getPlanificacionPendientesContexto");
    expect(controllerSrc).toMatch(/cache\.set\(distritoId,\s*\{[\s\S]*rows,[\s\S]*totalReported,[\s\S]*fetchedAt/);
  });

  it("caso B — revisita: cache hit sin request ni loading bloqueante", () => {
    const cacheHitBlock =
      controllerSrc.match(/if \(cached\) \{[\s\S]*?return;\s*\}/)?.[0] ?? "";
    expect(cacheHitBlock).toContain("setPendientesMapaRaw(cached.rows)");
    expect(cacheHitBlock).toContain("pendientesContexto: false");
    expect(cacheHitBlock).not.toContain("getPlanificacionPendientesContexto");
  });

  it("caso C — filtros/búsqueda/cards no refetchean M4", () => {
    expect(controllerSrc).not.toMatch(/\[cardActiva,\s*filtros\.q,\s*filtros\.rubro_id,\s*loadPendientesMapa\]/);
    expect(controllerSrc).not.toMatch(/\[filtros,\s*loadPendientesMapa\]/);
    expect(controllerSrc).toMatch(/sinPool\(pendientesMapaRaw, poolSet\)/);
    expect(controllerSrc).toMatch(/filtrarPendientesMapaPorCard/);
    expect(controllerSrc).toMatch(/filtrarPendientesMapaPorFiltros/);
  });

  it("caso D — agregar al pool no invalida cache", () => {
    const cache = new M4DistritoCache();
    cache.set(10, { rows: [{ id: 1 } as never], totalReported: 1, fetchedAt: Date.now() });
    invalidateM4CacheOnPoolRemoval(cache, [1], [1, 2], { 1: { iniciador_id: 1, distrito_id: 10 } as never });
    expect(cache.has(10)).toBe(true);
    expect(sinPool([{ id: 1 }, { id: 2 }], new Set([2])).map((r) => r.id)).toEqual([1]);
  });

  it("caso E — quitar pool invalida distrito resoluble", () => {
    const cache = new M4DistritoCache();
    cache.set(10, { rows: [{ id: 1 } as never], totalReported: 1, fetchedAt: Date.now() });
    invalidateM4CacheOnPoolRemoval(
      cache,
      [1],
      [],
      buildPoolRowsByIniciadorId([{ iniciador_id: 1, distrito_id: 10 } as never])
    );
    expect(cache.has(10)).toBe(false);
    expect(controllerSrc).toContain("invalidateM4CacheOnPoolRemoval");
  });

  it("caso F — quitar pool sin distrito resoluble limpia toda la cache", () => {
    const cache = new M4DistritoCache();
    cache.set(10, { rows: [{ id: 1 } as never], totalReported: 1, fetchedAt: Date.now() });
    invalidateM4CacheOnPoolRemoval(cache, [1], [], { 1: { iniciador_id: 1, distrito_id: null } as never });
    expect(cache.size()).toBe(0);
  });

  it("caso G — distrito null vacía raw pero conserva cache LRU", () => {
    expect(controllerSrc).toMatch(/if \(distritoActivoId == null\) \{[\s\S]*pendientesMapaReqSeq\.current \+= 1[\s\S]*setPendientesMapaRaw\(\[\]\)/);
    expect(controllerSrc).not.toMatch(/distritoActivoId == null[\s\S]*cache\.clear/);
  });

  it("caso H — race: cache hit incrementa secuencia antes de aplicar snapshot", () => {
    expect(controllerSrc).toMatch(/if \(cached\) \{[\s\S]*pendientesMapaReqSeq\.current \+= 1/);
    expect(controllerSrc).toMatch(/if \(seq !== pendientesMapaReqSeq\.current\) return/);
  });

  it("caso I — error parcial: cache.set solo tras paginación exitosa", () => {
    const setIndex = controllerSrc.indexOf("cache.set(distritoId");
    const catchIndex = controllerSrc.indexOf("} catch (e: unknown) {", setIndex);
    expect(setIndex).toBeGreaterThan(-1);
    expect(catchIndex).toBeGreaterThan(setIndex);
    expect(controllerSrc.slice(catchIndex)).not.toContain("cache.set(");
  });

  it("caso J — refreshPendientesMapa invalida distrito activo y fuerza fetch", () => {
    expect(controllerSrc).toContain("refreshPendientesMapa: () => loadPendientesMapa({ forceRefresh: true })");
    expect(controllerSrc).toMatch(/forceRefresh[\s\S]*cache\.delete\(distritoId\)/);
  });

  it("cache vive en controller con useRef (no en index.tsx)", () => {
    expect(controllerSrc).toContain("m4DistritoCacheRef = useRef(new M4DistritoCache())");
    expect(indexSrc).not.toContain("M4DistritoCache");
    expect(planificacionView).toContain("usePlanificacionController");
  });

  it("no implementa SWR ni TTL", () => {
    expect(cacheSrc).not.toContain("stale");
    expect(cacheSrc).not.toContain("TTL");
    const cacheHitBlock =
      controllerSrc.match(/if \(cached\) \{[\s\S]*?return;\s*\}/)?.[0] ?? "";
    expect(cacheHitBlock).not.toContain("getPlanificacionPendientesContexto");
    expect(controllerSrc).not.toContain("forceRefresh: false");
  });
});
