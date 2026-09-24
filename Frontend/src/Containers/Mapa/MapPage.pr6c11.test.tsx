/** @jsxImportSource react */
import { describe, expect, it } from "vitest";
import { existsSync, readFileSync } from "node:fs";
import { resolve } from "node:path";

const read = (rel: string) => readFileSync(resolve(process.cwd(), rel), "utf8");
const exists = (rel: string) => existsSync(resolve(process.cwd(), rel));

describe("PR6C.11 MapPage integra Geolocalización", () => {
  it("tabs muestran Geolocalización y Realizados, sin Pendientes", () => {
    const tabs = read("src/Containers/Mapa/Components/MapaModoTabs.tsx");
    expect(tabs).toContain('label="Geolocalización"');
    expect(tabs).toContain('value="geolocalizacion"');
    expect(tabs).toContain('label="Realizados"');
    expect(tabs).not.toContain('label="Pendientes"');
    expect(tabs).not.toContain('value="pendientes"');
  });

  it("MapPage monta vista compartida en modo geolocalizacion", () => {
    const mapPage = read("src/Containers/Mapa/MapPage.tsx");
    expect(mapPage).toContain("MapaDomiciliosGeolocalizacionView");
    expect(mapPage).toContain('modo === "geolocalizacion"');
    expect(mapPage).toContain('filterVariant="mapa"');
    expect(mapPage).toContain('actionVariant="icon"');
    expect(mapPage).toContain("showDetailPanel={false}");
    expect(mapPage).toContain("showHeader={false}");
    expect(mapPage).toContain('defaultStatus="requiere_accion"');
  });

  it("MapPage no usa loadPendientes ni flujo pendientes viejo", () => {
    const mapPage = read("src/Containers/Mapa/MapPage.tsx");
    expect(mapPage).not.toContain("loadPendientes");
    expect(mapPage).not.toContain("setGeoManual");
    expect(mapPage).not.toContain("setRelocalDraft");
    expect(mapPage).not.toContain('modo === "pendientes"');
    expect(mapPage).not.toContain("PanelResumenOperativo modo={modo}");
  });

  it("Realizados conserva filtros, panel y mapa operativo", () => {
    const mapPage = read("src/Containers/Mapa/MapPage.tsx");
    expect(mapPage).toContain("loadRealizados");
    expect(mapPage).toContain("MapaFiltrosUnificados");
    expect(mapPage).toContain("PanelResumenOperativo");
    expect(mapPage).toContain("MapaCanvas");
    expect(mapPage).toContain('modo === "realizados"');
  });

  it("/mapa abre geolocalizacion por defecto y soporta query modo", () => {
    const mapPage = read("src/Containers/Mapa/MapPage.tsx");
    expect(mapPage).toContain("useSearchParams");
    expect(mapPage).toContain('parseMapaModo');
    expect(mapPage).toContain('"geolocalizacion"');
    expect(mapPage).toContain('"realizados"');
    expect(mapPage).toContain('raw === "pendientes"');
    expect(mapPage).toContain('next.delete("modo")');
  });

  it("filtros unificados solo en realizados", () => {
    const mapPage = read("src/Containers/Mapa/MapPage.tsx");
    const realizadosBranch = mapPage.slice(mapPage.indexOf('modo === "geolocalizacion" ?'));
    expect(realizadosBranch).toContain("MapaFiltrosUnificados");
    const geoViewBlock = mapPage.slice(
      mapPage.indexOf("<MapaDomiciliosGeolocalizacionView"),
      mapPage.indexOf(') : (')
    );
    expect(geoViewBlock).not.toContain("MapaFiltrosUnificados");
  });
});

describe("PR6C.11 vista compartida variantes Mapa", () => {
  it("filtro mapa mockup implementado (PR6C.14/14b)", () => {
    const filtro = read(
      "src/Containers/Mapa/views/MapaDomiciliosGeolocalizacion/components/MapaDomiciliosGeolocalizacionFiltro.tsx"
    );
    expect(filtro).toContain('filterVariant === "mapa"');
    expect(filtro).toContain("MAPA_DOMICILIOS_SUBTABS.map");
    expect(filtro).toContain("glassTabsSecondaryPanelBarSx");
  });

  it("lista con iconos y chip debajo del domicilio", () => {
    const lista = read(
      "src/Containers/Mapa/views/MapaDomiciliosGeolocalizacion/components/MapaDomiciliosGeolocalizacionLista.tsx"
    );
    expect(lista).toContain('actionVariant === "icon"');
    expect(lista).toContain("IconButton");
    expect(lista).toContain("labelGeoChip");
    expect(lista).toContain("domicilio_linea");
  });
});

describe("PR6C.11 PR6C.15 sin wrapper temporal", () => {
  it("GestionarDomiciliosContainer eliminado; geolocalización vive en Mapa", () => {
    expect(exists("src/Containers/GestionarDomicilios/GestionarDomiciliosContainer.tsx")).toBe(
      false
    );
    const mapPage = read("src/Containers/Mapa/MapPage.tsx");
    expect(mapPage).toContain("MapaDomiciliosGeolocalizacionView");
    expect(mapPage).toContain('filterVariant="mapa"');
    expect(mapPage).toContain('actionVariant="icon"');
  });

  it("geolocalización usa getGestionDomicilios", () => {
    const hook = read(
      "src/Containers/Mapa/views/MapaDomiciliosGeolocalizacion/hooks/useGestionDomicilios.ts"
    );
    expect(hook).toContain("getGestionDomicilios");
    expect(hook).not.toContain("getMapPendientes");
    expect(hook).not.toContain("loadPendientes");
  });
});
