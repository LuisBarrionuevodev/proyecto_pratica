/** @jsxImportSource react */
import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const SHARED = "src/Containers/Mapa/views/MapaDomiciliosGeolocalizacion";
const read = (rel: string) => readFileSync(resolve(process.cwd(), rel), "utf8");

describe("Scroll hotfix — Mapa Geolocalización", () => {
  it("1. existe contenedor body scrolleable separado", () => {
    const lista = read(`${SHARED}/components/MapaDomiciliosGeolocalizacionLista.tsx`);
    expect(lista).toContain('className: "table-body"');
    expect(lista).toContain('overflowY: "auto"');
    expect(lista).toContain("mapGeoListaScrollSafeSx");
  });

  it("2. paginación/footer está fuera del body scrolleable", () => {
    const lista = read(`${SHARED}/components/MapaDomiciliosGeolocalizacionLista.tsx`);
    const layout = read(`${SHARED}/mapaGeolocalizacionLayout.ts`);
    expect(lista).toContain("enableBottomToolbar: !isMapaLayout");
    expect(lista).toContain('className="pagination-footer"');
    expect(lista).toContain("footer={mapaPaginationFooter}");
    expect(lista).toContain("<TablePagination");
    expect(layout).toContain("mapGeoListaPaginationFooterSx");
  });

  it("3. paginación se renderiza visible (footer fijo, no overflow hidden)", () => {
    const layout = read(`${SHARED}/mapaGeolocalizacionLayout.ts`);
    expect(layout).toContain("flexShrink: 0");
    expect(layout).toContain('overflow: "visible"');
    expect(layout).not.toContain('"& .MuiTablePagination-root": { overflow: "hidden" }');
  });

  it("4. panel mantiene altura fija", () => {
    const view = read(`${SHARED}/MapaDomiciliosGeolocalizacionView.tsx`);
    const layout = read(`${SHARED}/mapaGeolocalizacionLayout.ts`);
    expect(layout).toContain("MAP_GEO_PANEL_HEIGHT");
    expect(view).toContain("mapGeoPanelPaperSx");
  });

  it("5. última fila no queda tapada por footer", () => {
    const lista = read(`${SHARED}/components/MapaDomiciliosGeolocalizacionLista.tsx`);
    expect(lista).toContain("tr:last-of-type td");
    expect(lista).toContain("paddingBottom: 12");
  });

  it("6. Realizados sigue intacto", () => {
    const mapPage = read("src/Containers/Mapa/MapPage.tsx");
    expect(mapPage).toContain("loadRealizados");
    expect(mapPage).toContain("MapaCanvas");
    expect(mapPage).toContain("MapaFiltrosUnificados");
  });

  it("7. Geolocalización sigue intacta", () => {
    const view = read(`${SHARED}/MapaDomiciliosGeolocalizacionView.tsx`);
    expect(view).toContain("mapGeoListaScrollContainerSx");
    expect(view).toContain("layoutVariant=\"mapa\"");
  });
});
