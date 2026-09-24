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

describe("STAB-10b domicilios operativo", () => {
  it("useGestionDomicilios usa endpoint nuevo con debounce", () => {
    const src = read("src/Containers/Mapa/views/MapaDomiciliosGeolocalizacion/hooks/useGestionDomicilios.ts");
    expect(src).toContain("getGestionDomicilios");
    expect(src).toContain("appliedQ");
    expect(src).toContain("applySearch");
    expect(src).not.toContain("getMapPendientes");
  });

  it("vista refresca datos tras mutación vía refetch", () => {
    const src = read("src/Containers/Mapa/views/MapaDomiciliosGeolocalizacion/MapaDomiciliosGeolocalizacionView.tsx");
    expect(src).toContain("await refetch()");
    expect(src).toContain("onGuardarPuntoManual");
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
  it("MapPage: realizados carga con filtros; geolocalización usa vista compartida", () => {
    const mapPage = read("src/Containers/Mapa/MapPage.tsx");
    expect(mapPage).toContain("fetchInspectores");
    expect(mapPage).toContain("fetchDistritosCatalogo");
    expect(mapPage).toContain("loadRealizados");
    expect(mapPage).not.toContain("loadPendientes");
    expect(mapPage).toContain("MapaDomiciliosGeolocalizacionView");
    expect(mapPage).toContain("handleAplicar");
    expect(mapPage).toContain("forceNetwork: true");
  });

  it("useMapaOperativo: solo GET realizados GeoJSON", () => {
    const hook = read("src/Containers/Mapa/hooks/useMapaOperativo.ts");
    expect(hook).not.toContain("getMapOperativoPendientesFC");
    expect(hook).toContain("getMapOperativoRealizadosFC");
    expect(hook).toContain("setFeatures([])");
  });
});
