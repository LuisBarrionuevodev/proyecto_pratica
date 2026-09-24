/** @jsxImportSource react */
import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const SHARED = "src/Containers/Mapa/views/MapaDomiciliosGeolocalizacion";
const read = (rel: string) => readFileSync(resolve(process.cwd(), rel), "utf8");

describe("PR6C.14b patrón visual Relevamientos/Gestión", () => {
  it("1. tabs principales alineadas sin fullWidth (como RelevamientosSection)", () => {
    const tabs = read("src/Containers/Mapa/Components/MapaModoTabs.tsx");
    const relevSection = read("src/Containers/Relevamientos/RelevamientosSectionContainer.tsx");
    expect(tabs).toContain("moduleSlicesPanelPaperSx");
    expect(tabs).toContain("moduleSlicesTabsSx");
    expect(tabs).not.toContain('variant="fullWidth"');
    expect(relevSection).toContain("moduleSlicesPanelPaperSx");
    expect(relevSection).toContain("moduleSlicesTabsSx");
  });

  it("2. bloque Buscar domicilio con Limpiar y Filtrar estilo Relevamientos", () => {
    const filtro = read(`${SHARED}/components/MapaDomiciliosGeolocalizacionFiltro.tsx`);
    const mapaBlock = filtro.slice(filtro.indexOf('filterVariant === "mapa"'));
    expect(mapaBlock).toContain("filtroContainerStyles");
    expect(mapaBlock).toContain("filtroGridStyles");
    expect(mapaBlock).toContain("filtroButtonsStyles");
    expect(mapaBlock).toContain("Limpiar");
    expect(mapaBlock).toContain("Filtrar");
  });

  it("3. botón Filtrar compacto (dsSize sm, no ancho completo en botones)", () => {
    const filtro = read(`${SHARED}/components/MapaDomiciliosGeolocalizacionFiltro.tsx`);
    const mapaBlock = filtro.slice(
      filtro.indexOf('filterVariant === "mapa"'),
      filtro.indexOf('filterVariant === "chips"')
    );
    expect(mapaBlock).toContain("filtroButtonsStyles");
    expect(mapaBlock).toContain('dsSize="sm"');
    expect(mapaBlock).toContain("filtroButtonPrimaryStyles");
    expect(mapaBlock).not.toContain('dsSize="md"');
  });

  it("4. subtabs estilo slices secundarios Relevamientos", () => {
    const filtro = read(`${SHARED}/components/MapaDomiciliosGeolocalizacionFiltro.tsx`);
    const filters = read(`${SHARED}/mapaDomiciliosOperativoFilters.ts`);
    const relev = read("src/Containers/Relevamientos/RelevamientosContainer.tsx");
    const mapaBlock = filtro.slice(
      filtro.indexOf('filterVariant === "mapa"'),
      filtro.indexOf('filterVariant === "chips"')
    );
    expect(mapaBlock).toContain("glassTabsSecondaryPanelBarSx");
    expect(mapaBlock).toContain("glassSecondaryTabsSx");
    expect(mapaBlock).toContain('variant="scrollable"');
    expect(mapaBlock).not.toContain('variant="fullWidth"');
    expect(mapaBlock).toContain("MAPA_DOMICILIOS_SUBTABS.map");
    expect(relev).toContain("glassTabsSecondaryPanelBarSx");
    expect(relev).toContain("glassSecondaryTabsSx");
    expect(filters).toContain('"Para revisar"');
    expect(filters).toContain('"En el mapa"');
    expect(filters).toContain('"Validados"');
    expect(filters).toContain('"Todos"');
  });

  it("5. no aparecen chips viejos en variante mapa", () => {
    const filtro = read(`${SHARED}/components/MapaDomiciliosGeolocalizacionFiltro.tsx`);
    const mapaBlock = filtro.slice(filtro.indexOf('filterVariant === "mapa"'));
    expect(mapaBlock).not.toContain("Requieren acción");
    expect(mapaBlock).not.toContain("Sin punto");
    expect(mapaBlock).not.toContain("Punto dudoso");
  });

  it("6. tabla columnas Domicilio y Acción", () => {
    const lista = read(`${SHARED}/components/MapaDomiciliosGeolocalizacionLista.tsx`);
    expect(lista).toContain('header: "Domicilio"');
    expect(lista).toContain('header: "Acción"');
  });

  it("7. sin filtros internos MRT", () => {
    const lista = read(`${SHARED}/components/MapaDomiciliosGeolocalizacionLista.tsx`);
    expect(lista).toContain("enableGlobalFilter: false");
    expect(lista).toContain("enableColumnFilters: false");
  });

  it("8. sin panel inferior en Mapa", () => {
    const mapPage = read("src/Containers/Mapa/MapPage.tsx");
    expect(mapPage).toContain("showDetailPanel={false}");
  });

  it("9. layout mapa con paneles fijos y scroll interno (PR6C.14c)", () => {
    const view = read(`${SHARED}/MapaDomiciliosGeolocalizacionView.tsx`);
    expect(view).toContain("isMapaLayout");
    expect(view).toContain("moduleContentColumnSx");
    expect(view).not.toContain("functionalPageShellSx");
    expect(view).toContain("mapGeoPanelPaperSx");
    expect(view).toContain("mapGeoListaScrollContainerSx");
    expect(view).toContain('layoutVariant="mapa"');
  });

  it("10. endpoint y lógica intactos", () => {
    const hook = read(`${SHARED}/hooks/useGestionDomicilios.ts`);
    expect(hook).toContain("getGestionDomicilios");
    expect(hook).toContain("status_operativo");
    expect(hook).not.toContain("getMapPendientes");
    const mapPage = read("src/Containers/Mapa/MapPage.tsx");
    expect(mapPage).toContain("loadRealizados");
    expect(mapPage).toContain("MapaCanvas");
  });
});

describe("PR6C.14b relevamiento patrón Relevamientos", () => {
  it("documenta componentes y estilos copiados", () => {
    const relevSection = read("src/Containers/Relevamientos/RelevamientosSectionContainer.tsx");
    const relev = read("src/Containers/Relevamientos/RelevamientosContainer.tsx");
    const filtroRelev = read("src/Containers/Relevamientos/Components/FiltroRelevamientos.tsx");
    expect(relevSection).toMatch(/moduleSlicesPanelPaperSx[\s\S]*moduleSlicesTabsSx/);
    expect(relev).toMatch(/glassTabsSecondaryPanelBarSx[\s\S]*glassSecondaryTabsSx/);
    expect(filtroRelev).toContain("filtroContainerStyles");
    expect(filtroRelev).toContain('dsSize="sm"');
    expect(filtroRelev).toContain('dsVariant="ghost"');
    expect(relev).toContain("moduleContentColumnSx");
  });
});
