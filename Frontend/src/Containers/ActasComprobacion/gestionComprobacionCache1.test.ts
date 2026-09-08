import { describe, expect, it, vi } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import {
  createOperativaBaseCacheState,
  hasValidOperativaBase,
  invalidateOperativaBaseTabs,
  resolveOperativaTabLoadAction,
} from "./utils/operativaComprobacionBaseCache";
import {
  MUTATION_INVALIDATE_EXPEDIENTE,
  MUTATION_INVALIDATE_OFICIO,
  MUTATION_INVALIDATE_REINSPECCION,
  refreshComprobacionesPostOficio,
} from "./utils/refreshComprobacionesPostOficio";

const pagePath = resolve(process.cwd(), "src/Containers/ActasComprobacion/ActasComprobacionPage.tsx");
const pageSrc = () => readFileSync(pagePath, "utf8");

type RequestCounts = { expediente: number; oficio: number; reinspeccion: number };

function makeSession() {
  const cache = createOperativaBaseCacheState();
  const requests: RequestCounts = { expediente: 0, oficio: 0, reinspeccion: 0 };

  const loadExpediente = vi.fn(async () => {
    requests.expediente += 1;
    cache.expediente = { valid: true, snapshot: { items: [{ id: 1 } as never], total: 1 } };
  });
  const loadOficio = vi.fn(async () => {
    requests.oficio += 1;
    cache.oficio = { valid: true, snapshot: { items: [{ id: 2 } as never], total: 1 } };
  });
  const loadRein = vi.fn(async () => {
    requests.reinspeccion += 1;
    cache.reinspeccion = { valid: true, snapshot: { items: [{ id: 3 } as never], total: 1 } };
  });

  const visitTab = async (tab: "expediente" | "oficio" | "reinspeccion") => {
    const action = resolveOperativaTabLoadAction(tab, null, cache);
    if (action === "restore-base") return;
    if (tab === "expediente") await loadExpediente();
    if (tab === "oficio") await loadOficio();
    if (tab === "reinspeccion") await loadRein();
  };

  return { cache, requests, loadExpediente, loadOficio, loadRein, visitTab };
}

describe("operativaComprobacionBaseCache", () => {
  it("A/B: cambio de tab ya cargado no requiere nuevo fetch", async () => {
    const s = makeSession();
    await s.visitTab("expediente");
    await s.visitTab("oficio");
    await s.visitTab("expediente");
    await s.visitTab("oficio");
    expect(s.requests).toEqual({ expediente: 1, oficio: 1, reinspeccion: 0 });
    expect(resolveOperativaTabLoadAction("expediente", null, s.cache)).toBe("restore-base");
    expect(resolveOperativaTabLoadAction("oficio", null, s.cache)).toBe("restore-base");
  });

  it("C/D: filtrar no pisa base; limpiar restaura sin GET", async () => {
    const cache = createOperativaBaseCacheState();
    cache.expediente = {
      valid: true,
      snapshot: {
        items: [{ id: 1 } as never, { id: 2 } as never, { id: 3 } as never],
        total: 3,
      },
    };
    expect(resolveOperativaTabLoadAction("expediente", { desde: null, hasta: null, numeroComprobacion: "234" }, cache)).toBe(
      "fetch"
    );
    expect(resolveOperativaTabLoadAction("expediente", null, cache)).toBe("restore-base");
    expect(cache.expediente.snapshot?.items).toHaveLength(3);
  });

  it("E: cambio tab con filtro activo no invalida base", () => {
    const cache = createOperativaBaseCacheState();
    cache.expediente = { valid: true, snapshot: { items: [], total: 0 } };
    invalidateOperativaBaseTabs(cache, []);
    expect(hasValidOperativaBase(cache, "expediente")).toBe(true);
  });

  it("F: mutación invalida tabs afectados", async () => {
    const invalidateOperativaBaseTabsFn = vi.fn();
    const loadExpediente = vi.fn().mockResolvedValue(undefined);
    const loadOficio = vi.fn().mockResolvedValue(undefined);
    const loadRein = vi.fn().mockResolvedValue(undefined);

    await refreshComprobacionesPostOficio(
      {
        filters: null,
        activeTab: "expediente",
        invalidateOperativaBaseTabs: invalidateOperativaBaseTabsFn,
        loadExpediente,
        loadOficio,
        loadRein,
      },
      MUTATION_INVALIDATE_EXPEDIENTE
    );

    expect(invalidateOperativaBaseTabsFn).toHaveBeenCalledWith(MUTATION_INVALIDATE_EXPEDIENTE);
    expect(loadExpediente).toHaveBeenCalledWith(null, { silent: false, forceBaseRefresh: true });
    expect(loadOficio).toHaveBeenCalledWith(null, { silent: true, forceBaseRefresh: true });
    expect(loadRein).not.toHaveBeenCalled();

    await refreshComprobacionesPostOficio(
      {
        filters: null,
        activeTab: "oficio",
        invalidateOperativaBaseTabs: vi.fn(),
        loadExpediente,
        loadOficio,
        loadRein,
      },
      MUTATION_INVALIDATE_OFICIO
    );
    expect(loadRein).toHaveBeenCalledWith(null, { silent: true, forceBaseRefresh: true });

    await refreshComprobacionesPostOficio(
      {
        filters: null,
        activeTab: "reinspeccion",
        invalidateOperativaBaseTabs: vi.fn(),
        loadExpediente,
        loadOficio,
        loadRein,
      },
      MUTATION_INVALIDATE_REINSPECCION
    );
    expect(loadRein).toHaveBeenCalledWith(null, { silent: false, forceBaseRefresh: true });
  });
});

describe("ActasComprobacionPage CACHE.1", () => {
  it("usa operativaBaseCacheRef y no invalidatePendientesTabs en cambio de tab", () => {
    const s = pageSrc();
    expect(s).toContain("operativaBaseCacheRef");
    expect(s).toContain("createOperativaBaseCacheState");
    expect(s).not.toContain("invalidatePendientesTabs");
    expect(s).not.toContain("tabLoadedRef");
    expect(s).toContain("baseCacheHit");
  });
});
