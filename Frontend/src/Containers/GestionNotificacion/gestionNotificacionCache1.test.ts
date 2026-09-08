import { describe, expect, it, vi } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import {
  createOperativaNotificacionBaseCacheState,
  hasValidOperativaNotificacionBase,
  invalidateOperativaNotificacionBaseTabs,
  resolveOperativaNotificacionTabLoadAction,
} from "./utils/operativaNotificacionBaseCache";
import {
  MUTATION_INVALIDATE_ALL_OPERATIVE,
  MUTATION_INVALIDATE_PLAZO,
  MUTATION_INVALIDATE_REINSPECCION,
  refreshNotificacionesPostProrroga,
  resolveNotificacionMutationInvalidateTabs,
} from "./utils/refreshNotificacionesPostProrroga";

const pagePath = resolve(process.cwd(), "src/Containers/GestionNotificacion/GestionNotificacionPage.tsx");
const pageSrc = () => readFileSync(pagePath, "utf8");

type RequestCounts = { en_plazo: number; por_vencer: number; reinspeccion: number };

function makeSession() {
  const cache = createOperativaNotificacionBaseCacheState();
  const requests: RequestCounts = { en_plazo: 0, por_vencer: 0, reinspeccion: 0 };

  const loadPlazoSlice = vi.fn(async (slice: "en_plazo" | "por_vencer") => {
    requests[slice] += 1;
    cache[slice] = { valid: true, snapshot: { items: [{ id: slice === "en_plazo" ? 1 : 2 } as never], total: 1 } };
  });
  const loadReinspeccion = vi.fn(async () => {
    requests.reinspeccion += 1;
    cache.reinspeccion = { valid: true, snapshot: { items: [{ id: 3 } as never], total: 1 } };
  });

  const visitPlazo = async (slice: "en_plazo" | "por_vencer") => {
    const action = resolveOperativaNotificacionTabLoadAction(slice, null, cache);
    if (action === "restore-base") return;
    await loadPlazoSlice(slice);
  };

  const visitReinspeccion = async () => {
    const action = resolveOperativaNotificacionTabLoadAction("reinspeccion", null, cache);
    if (action === "restore-base") return;
    await loadReinspeccion();
  };

  return { cache, requests, loadPlazoSlice, loadReinspeccion, visitPlazo, visitReinspeccion };
}

describe("operativaNotificacionBaseCache", () => {
  it("A: En plazo → Por vencer → En plazo — un GET por slice de plazo", async () => {
    const s = makeSession();
    await s.visitPlazo("en_plazo");
    await s.visitPlazo("por_vencer");
    await s.visitPlazo("en_plazo");
    expect(s.requests).toEqual({ en_plazo: 1, por_vencer: 1, reinspeccion: 0 });
    expect(resolveOperativaNotificacionTabLoadAction("en_plazo", null, s.cache)).toBe("restore-base");
  });

  it("B: Por vencer → Reinspección → Por vencer — un GET por slice", async () => {
    const s = makeSession();
    await s.visitPlazo("por_vencer");
    await s.visitReinspeccion();
    await s.visitPlazo("por_vencer");
    expect(s.requests).toEqual({ en_plazo: 0, por_vencer: 1, reinspeccion: 1 });
    expect(resolveOperativaNotificacionTabLoadAction("por_vencer", null, s.cache)).toBe("restore-base");
  });

  it("C: Reinspección → En plazo → Reinspección — un GET RN", async () => {
    const s = makeSession();
    await s.visitReinspeccion();
    await s.visitPlazo("en_plazo");
    await s.visitReinspeccion();
    expect(s.requests.reinspeccion).toBe(1);
    expect(resolveOperativaNotificacionTabLoadAction("reinspeccion", null, s.cache)).toBe("restore-base");
  });

  it("D/E: filtrar no pisa base; limpiar restaura sin GET", () => {
    const cache = createOperativaNotificacionBaseCacheState();
    cache.en_plazo = {
      valid: true,
      snapshot: {
        items: [{ id: 1 } as never, { id: 2 } as never, { id: 3 } as never],
        total: 42,
      },
    };
    expect(
      resolveOperativaNotificacionTabLoadAction(
        "en_plazo",
        { desde: null, hasta: null, numeroNotificacion: "123", calleQ: null },
        cache
      )
    ).toBe("fetch");
    expect(resolveOperativaNotificacionTabLoadAction("en_plazo", null, cache)).toBe("restore-base");
    expect(cache.en_plazo.snapshot?.items).toHaveLength(3);
    expect(cache.en_plazo.snapshot?.total).toBe(42);
  });

  it("F: cambio tab con filtro no invalida base", () => {
    const cache = createOperativaNotificacionBaseCacheState();
    cache.en_plazo = { valid: true, snapshot: { items: [], total: 0 } };
    invalidateOperativaNotificacionBaseTabs(cache, []);
    expect(hasValidOperativaNotificacionBase(cache, "en_plazo")).toBe(true);
  });

  it("G: mutación plazo invalida solo en_plazo y por_vencer", async () => {
    const invalidateOperativaBaseTabs = vi.fn();
    const loadPlazoSlice = vi.fn().mockResolvedValue(undefined);
    const loadReinspeccion = vi.fn().mockResolvedValue(undefined);

    await refreshNotificacionesPostProrroga(
      {
        activeSlice: "en_plazo",
        invalidateOperativaBaseTabs,
        loadPlazoSlice,
        loadReinspeccion,
      },
      MUTATION_INVALIDATE_PLAZO
    );

    expect(invalidateOperativaBaseTabs).toHaveBeenCalledWith(MUTATION_INVALIDATE_PLAZO);
    expect(loadPlazoSlice).toHaveBeenCalledWith("en_plazo", null, { silent: false, forceBaseRefresh: true });
    expect(loadPlazoSlice).toHaveBeenCalledWith("por_vencer", null, { silent: true, forceBaseRefresh: true });
    expect(loadReinspeccion).not.toHaveBeenCalled();
  });

  it("mutación RN invalida solo reinspeccion", async () => {
    const loadPlazoSlice = vi.fn().mockResolvedValue(undefined);
    const loadReinspeccion = vi.fn().mockResolvedValue(undefined);

    await refreshNotificacionesPostProrroga(
      {
        activeSlice: "vencidas_o_hoy",
        invalidateOperativaBaseTabs: vi.fn(),
        loadPlazoSlice,
        loadReinspeccion,
      },
      MUTATION_INVALIDATE_REINSPECCION
    );

    expect(loadReinspeccion).toHaveBeenCalledWith(null, { silent: false, forceBaseRefresh: true });
    expect(loadPlazoSlice).not.toHaveBeenCalled();
  });

  it("sync vencidas invalida los tres slices", async () => {
    const loadPlazoSlice = vi.fn().mockResolvedValue(undefined);
    const loadReinspeccion = vi.fn().mockResolvedValue(undefined);

    await refreshNotificacionesPostProrroga(
      {
        activeSlice: "por_vencer",
        invalidateOperativaBaseTabs: vi.fn(),
        loadPlazoSlice,
        loadReinspeccion,
      },
      MUTATION_INVALIDATE_ALL_OPERATIVE
    );

    expect(loadPlazoSlice).toHaveBeenCalledWith("en_plazo", null, { silent: true, forceBaseRefresh: true });
    expect(loadPlazoSlice).toHaveBeenCalledWith("por_vencer", null, { silent: false, forceBaseRefresh: true });
    expect(loadReinspeccion).toHaveBeenCalledWith(null, { silent: true, forceBaseRefresh: true });
  });

  it("resolveNotificacionMutationInvalidateTabs desde reinspección invalida todo", () => {
    expect(resolveNotificacionMutationInvalidateTabs("vencidas_o_hoy", false)).toEqual(
      MUTATION_INVALIDATE_ALL_OPERATIVE
    );
    expect(resolveNotificacionMutationInvalidateTabs("en_plazo", true)).toEqual(
      MUTATION_INVALIDATE_ALL_OPERATIVE
    );
    expect(resolveNotificacionMutationInvalidateTabs("en_plazo", false)).toEqual(MUTATION_INVALIDATE_PLAZO);
  });
});

describe("GestionNotificacionPage CACHE.1", () => {
  it("usa operativaBaseCacheRef y restore-base sin force en tab change", () => {
    const s = pageSrc();
    expect(s).toContain("operativaBaseCacheRef");
    expect(s).toContain("createOperativaNotificacionBaseCacheState");
    expect(s).toContain("baseCacheHit");
    expect(s).toContain("operativeBaseTotals");
    expect(s).not.toContain("operativeSliceLoadedRef");
    expect(s).not.toContain("itemsBySlice");
    expect(s).not.toContain("reinspeccionDataLoadedRef");
    expect(s).not.toContain("loadPlazoSliceData(plazoSlice, tabChanged");
  });
});
