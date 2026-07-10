/** @jsxImportSource react */
import { existsSync } from "node:fs";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

const read = (rel: string) => readFileSync(resolve(process.cwd(), rel), "utf8");
const exists = (rel: string) => existsSync(resolve(process.cwd(), rel));

const LEGACY_REMOVED = [
  "src/Containers/Mapa/Components/MapView.tsx",
  "src/Containers/Mapa/Components/MapViewGeo.tsx",
  "src/Containers/Mapa/hooks/usePendientes.ts",
  "src/Containers/Mapa/hooks/useUpdateDomicilio.ts",
  "src/Containers/Mapa/Components/SearchBar.tsx",
  "src/Containers/Mapa/Components/MapClickHandler.tsx",
  "src/Containers/Mapa/Components/AddLocalForm.tsx",
  "src/Containers/Mapa/Components/PolygonForm.tsx",
  "src/Containers/Mapa/Components/DistrictFilter.tsx",
];

describe("PR6C.13 limpieza legacy Pendientes operativo", () => {
  it("elimina archivos legacy no enrutados", () => {
    for (const path of LEGACY_REMOVED) {
      expect(exists(path), `legacy aún presente: ${path}`).toBe(false);
    }
  });

  it("useMapaOperativo sin loadPendientes ni getMapOperativoPendientesFC", () => {
    const hook = read("src/Containers/Mapa/hooks/useMapaOperativo.ts");
    expect(hook).not.toContain("loadPendientes");
    expect(hook).not.toContain("getMapOperativoPendientesFC");
    expect(hook).toContain("loadRealizados");
    expect(hook).toContain("getMapOperativoRealizadosFC");
  });

  it("MapPage sin loadPendientes ni relocalización vieja", () => {
    const mapPage = read("src/Containers/Mapa/MapPage.tsx");
    expect(mapPage).not.toContain("loadPendientes");
    expect(mapPage).not.toContain("relocalDraft");
    expect(mapPage).not.toContain("setGeoManual");
    expect(mapPage).not.toContain('modo === "pendientes"');
    expect(mapPage).toContain("loadRealizados");
    expect(mapPage).toContain("MapaDomiciliosGeolocalizacionView");
  });

  it("MapaCanvas sin RelocalizarControl ni iniciador_backlog", () => {
    const canvas = read("src/Containers/Mapa/Components/MapaCanvas.tsx");
    expect(canvas).not.toContain("RelocalizarControl");
    expect(canvas).not.toContain("iniciador_backlog");
    expect(canvas).not.toContain("ruta_en_proceso");
    expect(canvas).not.toContain("relocalDraft");
    expect(canvas).toContain("MapaRealizadoPopup");
  });

  it("PanelResumenOperativo solo realizados", () => {
    const panel = read("src/Containers/Mapa/Components/PanelResumenOperativo.tsx");
    expect(panel).not.toContain('modo === "pendientes"');
    expect(panel).not.toContain("iniciador_backlog");
    expect(panel).toContain("Visitas realizadas");
  });

  it("MapaFiltrosUnificados sin pendienteTipo", () => {
    const filtro = read("src/Containers/Mapa/Components/MapaFiltrosUnificados.tsx");
    expect(filtro).not.toContain("pendienteTipo");
    expect(filtro).not.toContain('modo === "pendientes"');
    expect(filtro).toContain("Definición");
    expect(filtro).toContain("Inspector");
  });
});

describe("PR6C.13 modos activos intactos", () => {
  it("/mapa default Geolocalización", () => {
    const mapPage = read("src/Containers/Mapa/MapPage.tsx");
    expect(mapPage).toContain('modo === "geolocalizacion"');
    expect(mapPage).toContain('filterVariant="mapa"');
  });

  it("/mapa?modo=realizados conserva flujo operativo", () => {
    const mapPage = read("src/Containers/Mapa/MapPage.tsx");
    expect(mapPage).toContain('"realizados"');
    expect(mapPage).toContain("MapaFiltrosUnificados");
    expect(mapPage).toContain("PanelResumenOperativo");
    expect(mapPage).toContain("MapaCanvas");
  });

  it("Geolocalización sigue usando getGestionDomicilios", () => {
    const hook = read(
      "src/Containers/Mapa/views/MapaDomiciliosGeolocalizacion/hooks/useGestionDomicilios.ts"
    );
    expect(hook).toContain("getGestionDomicilios");
  });

  it("tabs sin Pendientes viejo", () => {
    const tabs = read("src/Containers/Mapa/Components/MapaModoTabs.tsx");
    expect(tabs).toContain("Geolocalización");
    expect(tabs).not.toContain('label="Pendientes"');
    expect(tabs).not.toContain('value="pendientes"');
  });
});
