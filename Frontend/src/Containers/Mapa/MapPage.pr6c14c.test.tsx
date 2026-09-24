/** @jsxImportSource react */
import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const SHARED = "src/Containers/Mapa/views/MapaDomiciliosGeolocalizacion";
const read = (rel: string) => readFileSync(resolve(process.cwd(), rel), "utf8");

describe("PR6C.14c layout fino Geolocalización", () => {
  it("1. panel lista con contenedor scrollable interno", () => {
    const view = read(`${SHARED}/MapaDomiciliosGeolocalizacionView.tsx`);
    const lista = read(`${SHARED}/components/MapaDomiciliosGeolocalizacionLista.tsx`);
    const layout = read(`${SHARED}/mapaGeolocalizacionLayout.ts`);
    expect(layout).toContain("mapGeoListaScrollContainerSx");
    expect(view).toContain("mapGeoListaScrollContainerSx");
    expect(lista).toContain('overflowY: "auto"');
    expect(lista).toContain("enableStickyHeader: isMapaLayout");
  });

  it("2. overlay del mapa usa estilo glass sólido", () => {
    const mapa = read(`${SHARED}/components/MapaDomiciliosGeolocalizacionMapPanel.tsx`);
    const layout = read(`${SHARED}/mapaGeolocalizacionLayout.ts`);
    expect(mapa).toContain("mapEditOverlayGlassSx");
    expect(layout).toContain("mapEditOverlayGlassSx");
    expect(layout).toContain("backdropFilter");
    expect(layout).toContain("0.94");
  });

  it("3. overlay no usa transparencia mínima (moduleFiltersSurfaceSx)", () => {
    const mapa = read(`${SHARED}/components/MapaDomiciliosGeolocalizacionMapPanel.tsx`);
    expect(mapa).not.toContain("moduleFiltersSurfaceSx");
    const layout = read(`${SHARED}/mapaGeolocalizacionLayout.ts`);
    expect(layout).not.toContain("0.035");
  });

  it("4. overlay desplazado a la derecha sin tapar zoom", () => {
    const layout = read(`${SHARED}/mapaGeolocalizacionLayout.ts`);
    expect(layout).toContain("left: 56");
    expect(layout).toContain("right: 72");
  });

  it("5. mapa y lista con altura fija equivalente", () => {
    const view = read(`${SHARED}/MapaDomiciliosGeolocalizacionView.tsx`);
    const layout = read(`${SHARED}/mapaGeolocalizacionLayout.ts`);
    expect(layout).toContain("MAP_GEO_PANEL_HEIGHT");
    expect(view).toContain("mapGeoPanelPaperSx");
    expect(view).toContain("height={mapPanelHeight}");
    expect(view).toContain('? "100%"');
  });

  it("6. sin panel inferior en Mapa", () => {
    const mapPage = read("src/Containers/Mapa/MapPage.tsx");
    expect(mapPage).toContain("showDetailPanel={false}");
  });

  it("7. columnas Domicilio y Acción intactas", () => {
    const lista = read(`${SHARED}/components/MapaDomiciliosGeolocalizacionLista.tsx`);
    expect(lista).toContain('header: "Domicilio"');
    expect(lista).toContain('header: "Acción"');
  });

  it("8. Realizados intacto", () => {
    const mapPage = read("src/Containers/Mapa/MapPage.tsx");
    expect(mapPage).toContain("loadRealizados");
    expect(mapPage).toContain("MapaCanvas");
    expect(mapPage).toContain("MapaFiltrosUnificados");
  });
});
