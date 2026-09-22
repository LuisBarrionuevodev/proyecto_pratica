import { describe, expect, it, vi } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import {
  createOperativaBaseCacheState,
  resolveOperativaTabLoadAction,
} from "./utils/operativaComprobacionBaseCache";
import {
  createOperativaMemoryByTab,
  operativaFiltersSignature,
  resolveOperativaTabAppliedFilters,
  shouldSwapOperativaTabMemory,
  snapshotOperativaFiltroMemory,
} from "./utils/operativaComprobacionTabMemory";
import {
  MUTATION_INVALIDATE_EXPEDIENTE,
  refreshComprobacionesPostOficio,
} from "./utils/refreshComprobacionesPostOficio";

const pagePath = resolve(process.cwd(), "src/Containers/ActasComprobacion/ActasComprobacionPage.tsx");
const pageSrc = () => readFileSync(pagePath, "utf8");

type RequestCounts = { expediente: number; oficio: number; reinspeccion: number };

function makeTabSession() {
  const cache = createOperativaBaseCacheState();
  const memory = createOperativaMemoryByTab();
  const loadedSig: Record<"expediente" | "oficio" | "reinspeccion", string | null> = {
    expediente: null,
    oficio: null,
    reinspeccion: null,
  };
  const requests: RequestCounts = { expediente: 0, oficio: 0, reinspeccion: 0 };
  const paginationByTab = {
    expediente: { pageIndex: 0, pageSize: 10 },
    oficio: { pageIndex: 0, pageSize: 10 },
    reinspeccion: { pageIndex: 0, pageSize: 10 },
  };

  const loadExpediente = vi.fn(async (filters: unknown) => {
    requests.expediente += 1;
    loadedSig.expediente = operativaFiltersSignature(filters as null);
    cache.expediente = { valid: true, snapshot: { items: [{ id: 1 } as never], total: 1 } };
  });
  const loadOficio = vi.fn(async (filters: unknown) => {
    requests.oficio += 1;
    loadedSig.oficio = operativaFiltersSignature(filters as null);
    cache.oficio = { valid: true, snapshot: { items: [{ id: 2 } as never], total: 1 } };
  });
  const loadRein = vi.fn(async (filters: unknown) => {
    requests.reinspeccion += 1;
    loadedSig.reinspeccion = operativaFiltersSignature(filters as null);
    cache.reinspeccion = { valid: true, snapshot: { items: [{ id: 3 } as never], total: 1 } };
  });

  const visitTab = async (tab: "expediente" | "oficio" | "reinspeccion") => {
    const filters = resolveOperativaTabAppliedFilters(tab, memory);
    const sig = operativaFiltersSignature(filters);
    if (loadedSig[tab] === sig) return;
    const action = resolveOperativaTabLoadAction(tab, filters, cache);
    if (action === "restore-base") {
      loadedSig[tab] = sig;
      return;
    }
    if (tab === "expediente") await loadExpediente(filters);
    if (tab === "oficio") await loadOficio(filters);
    if (tab === "reinspeccion") await loadRein(filters);
  };

  const swapTabs = (from: "expediente" | "oficio" | "reinspeccion", to: "expediente" | "oficio" | "reinspeccion") => {
    if (shouldSwapOperativaTabMemory(from, to)) {
      memory[from].table.pagination = { ...paginationByTab[from] };
      const target = memory[to];
      paginationByTab[to] = { ...target.table.pagination };
    }
  };

  return {
    cache,
    memory,
    loadedSig,
    requests,
    paginationByTab,
    loadExpediente,
    loadOficio,
    loadRein,
    visitTab,
    swapTabs,
  };
}

describe("COMP-GESTION-MEMORY.2 operativaComprobacionTabMemory", () => {
  it("A: paginación por tab se conserva al intercambiar bandejas", () => {
    const memory = createOperativaMemoryByTab();
    memory.expediente.table.pagination = { pageIndex: 2, pageSize: 10 };
    memory.oficio.table.pagination = { pageIndex: 0, pageSize: 10 };

    const paginationByTab = { expediente: { pageIndex: 2, pageSize: 10 }, oficio: { pageIndex: 0, pageSize: 10 } };
    memory.expediente.table.pagination = { ...paginationByTab.expediente };
    memory.oficio.table.pagination = { pageIndex: 1, pageSize: 10 };
    paginationByTab.oficio = { ...memory.oficio.table.pagination };

    expect(paginationByTab.expediente.pageIndex).toBe(2);
    expect(memory.expediente.table.pagination.pageIndex).toBe(2);
    expect(memory.oficio.table.pagination.pageIndex).toBe(1);
  });

  it("B: no refetch al volver si firma de filtros ya cargada", async () => {
    const s = makeTabSession();
    await s.visitTab("expediente");
    await s.visitTab("oficio");
    await s.visitTab("expediente");
    expect(s.requests).toEqual({ expediente: 1, oficio: 1, reinspeccion: 0 });
    expect(s.loadExpediente).toHaveBeenCalledTimes(1);
  });

  it("C: filtro aplicado no se reemplaza por base al resolver tab", () => {
    const memory = createOperativaMemoryByTab();
    memory.expediente.filtro = snapshotOperativaFiltroMemory(
      {
        desde: null,
        hasta: null,
        numeroComprobacion: "Juan Pérez",
        expedienteEnvioNumero: "",
        numeroOficio: "",
        expedienteRespuestaNumero: "",
      },
      { desde: null, hasta: null, numeroComprobacion: "Juan Pérez" }
    );
    const filters = resolveOperativaTabAppliedFilters("expediente", memory);
    expect(filters?.numeroComprobacion).toBe("Juan Pérez");
    expect(operativaFiltersSignature(filters)).not.toBe(operativaFiltersSignature(null));
  });

  it("D: mutación invalida expediente y oficio sin tocar reinspección", async () => {
    const loadExpediente = vi.fn().mockResolvedValue(undefined);
    const loadOficio = vi.fn().mockResolvedValue(undefined);
    const loadRein = vi.fn().mockResolvedValue(undefined);

    await refreshComprobacionesPostOficio(
      {
        filters: null,
        activeTab: "expediente",
        invalidateOperativaBaseTabs: vi.fn(),
        loadExpediente,
        loadOficio,
        loadRein,
      },
      MUTATION_INVALIDATE_EXPEDIENTE
    );

    expect(loadExpediente).toHaveBeenCalledWith(null, { silent: false, forceBaseRefresh: true });
    expect(loadOficio).toHaveBeenCalledWith(null, { silent: true, forceBaseRefresh: true });
    expect(loadRein).not.toHaveBeenCalled();
  });

  it("E: memoria de expediente persiste al salir a recorrido y volver", () => {
    const memory = createOperativaMemoryByTab();
    memory.expediente.filtro = snapshotOperativaFiltroMemory(
      {
        desde: "2026-01-01",
        hasta: "2026-01-31",
        numeroComprobacion: "99",
        expedienteEnvioNumero: "",
        numeroOficio: "",
        expedienteRespuestaNumero: "",
      },
      { desde: "2026-01-01", hasta: "2026-01-31", numeroComprobacion: "99" }
    );
    memory.expediente.table.pagination = { pageIndex: 3, pageSize: 10 };
    const restored = memory.expediente;
    expect(restored.filtro.applied?.numeroComprobacion).toBe("99");
    expect(restored.table.pagination.pageIndex).toBe(3);
  });

  it("F: sort por tab independiente", () => {
    const memory = createOperativaMemoryByTab();
    memory.expediente.table.sorting = [{ id: "fecha_ot", desc: true }];
    memory.oficio.table.sorting = [{ id: "establecimiento", desc: false }];
    expect(memory.expediente.table.sorting[0]?.id).toBe("fecha_ot");
    expect(memory.oficio.table.sorting[0]?.id).toBe("establecimiento");
  });
});

describe("COMP-GESTION-MEMORY.2 ActasComprobacionPage static", () => {
  it("G: una sola tabla operativa compartida (sin tres MRT condicionales)", () => {
    const s = pageSrc();
    expect(s).toContain("ComprobacionOperativaBandejaTable");
    expect(s).toContain("mostrarTablaOperativa");
    expect(s).toContain("operativaMemoryByTabRef");
    expect(s).toContain("opPagination");
    expect(s).toContain("opSorting");
    expect(s).not.toMatch(/\{tab === "expediente" &&[\s\S]*?<MaterialReactTable table=\{tableExpediente\}/);
    expect(s).not.toMatch(/\{tab === "oficio" &&[\s\S]*?<MaterialReactTable table=\{tableOficio\}/);
    expect(s).not.toMatch(/\{tab === "reinspeccion" &&[\s\S]*?<MaterialReactTable table=\{tableRein\}/);
    expect(s).not.toContain("tableExpediente");
    expect(s).not.toContain("tableOficio");
    expect(s).not.toContain("tableRein");
    expect(s).not.toContain('ensureTabLoaded(tab, { filters: null })');
    expect(s).toContain("resolveOperativaTabAppliedFilters");
  });
});
