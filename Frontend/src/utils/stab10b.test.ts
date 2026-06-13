import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const read = (rel: string) => readFileSync(resolve(process.cwd(), rel), "utf8");

describe("STAB-10b M4 mapa liviano", () => {
  it("controller pide fields=minimal solo en carga mapa", () => {
    const src = read("src/Containers/RutasTrabajo/planificacion/hooks/usePlanificacionController.ts");
    expect(src).toContain('fields: "minimal"');
    expect(src).toContain("M4_PAGE_MAP_CHUNK");
    expect(src).toContain("M4_MAP_MAX_PAGES");
    const mapBlock = src.slice(src.indexOf("M4 mapa"));
    const listBlock = src.slice(0, src.indexOf("M4 mapa"));
    expect(mapBlock).toContain('fields: "minimal"');
    expect(listBlock).not.toContain('fields: "minimal"');
  });

  it("API expone fields en IPendientesContextoParams", () => {
    const src = read("src/Containers/RutasTrabajo/planificacion/api/planificacionApi.ts");
    expect(src).toContain('fields?: "full" | "minimal"');
  });

  it("KPIs siguen usando pendientesMapaRaw / metricasVisibles", () => {
    const view = read("src/Containers/RutasTrabajo/planificacion/PlanificacionView.tsx");
    const ctrl = read("src/Containers/RutasTrabajo/planificacion/hooks/usePlanificacionController.ts");
    expect(view).toContain("metricasVisibles");
    expect(ctrl).toContain("pendientesMapaRaw");
    expect(ctrl).toContain("computeMetricasCardsDesdeMapa");
  });
});

describe("STAB-10b domicilios cache", () => {
  it("cachea por pestaña y filtros", () => {
    const src = read("src/Containers/GestionarDomicilios/hooks/useDomiciliosPendientes.ts");
    expect(src).toContain("tabCacheRef");
    expect(src).toContain("filtersCacheKey");
    expect(src).toContain("cached?.key === filtersCacheKey");
  });

  it("refetch invalida cache antes de recargar", () => {
    const src = read("src/Containers/GestionarDomicilios/hooks/useDomiciliosPendientes.ts");
    expect(src).toContain("invalidateCache");
    const refetchBlock = src.slice(src.indexOf("const refetch"));
    expect(refetchBlock).toContain("invalidateCache()");
  });

  it("container sigue llamando refetch tras mutación", () => {
    const src = read("src/Containers/GestionarDomicilios/GestionarDomiciliosContainer.tsx");
    expect(src).toContain("refetch");
  });
});

describe("STAB-10b PendientesContextoPanel estilos compactos", () => {
  it("usa filterCompact* como UrgentesFiltroPanel", () => {
    const src = read("src/Containers/RutasTrabajo/planificacion/PendientesContextoFiltroPanel.tsx");
    expect(src).toContain("filterCompactActionsSx");
    expect(src).toContain("filterCompactPrimaryButtonSx");
    expect(src).toContain("filterCompactSecondaryButtonSx");
    expect(src).toContain("Limpiar");
    expect(src).not.toContain("RefreshIcon");
  });
});

describe("STAB-10b diagnóstico mapa operativo (análisis estático)", () => {
  it("MapPage: requests al montar y al cambiar filtros aplicados", () => {
    const mapPage = read("src/Containers/Mapa/MapPage.tsx");
    expect(mapPage).toContain("fetchInspectores");
    expect(mapPage).toContain("fetchDistritosCatalogo");
    expect(mapPage).toContain("loadPendientes(loadParamsPendientes)");
    expect(mapPage).toContain("handleAplicar");
    expect(mapPage).toContain("forceNetwork: true");
  });

  it("useMapaOperativo: un GET GeoJSON por carga", () => {
    const hook = read("src/Containers/Mapa/hooks/useMapaOperativo.ts");
    expect(hook).toContain("getMapOperativoPendientesFC");
    expect(hook).toContain("getMapOperativoRealizadosFC");
    expect(hook).toContain("setFeatures([])");
  });
});
