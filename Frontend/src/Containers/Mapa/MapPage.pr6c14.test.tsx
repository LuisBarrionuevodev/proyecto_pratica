/** @jsxImportSource react */
import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const SHARED = "src/Containers/Mapa/views/MapaDomiciliosGeolocalizacion";
const read = (rel: string) => readFileSync(resolve(process.cwd(), rel), "utf8");

describe("PR6C.14 mockup visual Geolocalización", () => {
  it("1. renderiza tabs principales Geolocalización / Realizados", () => {
    const tabs = read("src/Containers/Mapa/Components/MapaModoTabs.tsx");
    expect(tabs).toContain('label="Geolocalización"');
    expect(tabs).toContain('label="Realizados"');
    expect(tabs).toContain("moduleSlicesTabsSx");
    expect(tabs).toContain("moduleSlicesPanelPaperSx");
    expect(tabs).not.toContain('variant="fullWidth"');
  });

  it("2. renderiza bloque Buscar domicilio con Limpiar y Filtrar", () => {
    const filtro = read(`${SHARED}/components/MapaDomiciliosGeolocalizacionFiltro.tsx`);
    expect(filtro).toContain('filterVariant === "mapa"');
    expect(filtro).toContain("Buscar domicilio");
    expect(filtro).toContain("Limpiar");
    expect(filtro).toContain("Filtrar");
    expect(filtro).toContain("filtroContainerStyles");
    const mapPage = read("src/Containers/Mapa/MapPage.tsx");
    expect(mapPage).toContain('filterVariant="mapa"');
  });

  it("3. renderiza subtabs Para revisar / En el mapa / Validados / Todos", () => {
    const filters = read(`${SHARED}/mapaDomiciliosOperativoFilters.ts`);
    expect(filters).toContain("MAPA_DOMICILIOS_SUBTABS");
    expect(filters).toContain('"Para revisar"');
    expect(filters).toContain('"En el mapa"');
    expect(filters).toContain('"Validados"');
    expect(filters).toContain('"Todos"');
    const filtro = read(`${SHARED}/components/MapaDomiciliosGeolocalizacionFiltro.tsx`);
    expect(filtro).toContain("MAPA_DOMICILIOS_SUBTABS.map");
    expect(filtro).toContain("glassTabsSecondaryPanelBarSx");
  });

  it("4. no renderiza chips viejos en variante mapa", () => {
    const filtro = read(`${SHARED}/components/MapaDomiciliosGeolocalizacionFiltro.tsx`);
    const mapaBlock = filtro.slice(filtro.indexOf('filterVariant === "mapa"'));
    expect(mapaBlock).not.toContain("Requieren acción");
    expect(mapaBlock).not.toContain("Sin punto");
    expect(mapaBlock).not.toContain("Punto dudoso");
    expect(mapaBlock).not.toContain("Manuales");
    expect(mapaBlock).not.toContain("Geolocalizados");
  });

  it("5. lista tiene columnas Domicilio y Acción", () => {
    const lista = read(`${SHARED}/components/MapaDomiciliosGeolocalizacionLista.tsx`);
    expect(lista).toContain('header: "Domicilio"');
    expect(lista).toContain('header: "Acción"');
  });

  it("6. chip EN MAPA aparece debajo del domicilio", () => {
    const filters = read(`${SHARED}/mapaDomiciliosOperativoFilters.ts`);
    const lista = read(`${SHARED}/components/MapaDomiciliosGeolocalizacionLista.tsx`);
    expect(filters).toContain("EN MAPA");
    expect(lista).toContain("labelGeoChip");
    expect(lista).toContain("domicilio_linea");
  });

  it("7. chip SIN COORDS aparece debajo del domicilio", () => {
    const filters = read(`${SHARED}/mapaDomiciliosOperativoFilters.ts`);
    expect(filters).toContain("SIN COORDS");
  });

  it("8. acción es ícono, no botón de texto", () => {
    const lista = read(`${SHARED}/components/MapaDomiciliosGeolocalizacionLista.tsx`);
    expect(lista).toContain("IconButton");
    expect(lista).toContain("AddLocationAltIcon");
    expect(lista).toContain("EditLocationAltIcon");
    const mapPage = read("src/Containers/Mapa/MapPage.tsx");
    expect(mapPage).toContain('actionVariant="icon"');
  });

  it("9. click en marker activa reubicar sin panel inferior", () => {
    const view = read(`${SHARED}/MapaDomiciliosGeolocalizacionView.tsx`);
    expect(view).toContain("handleMapPointSelect");
    expect(view).toContain("startReubicar(row)");
    expect(view).toContain("showDetailPanel");
    const mapPage = read("src/Containers/Mapa/MapPage.tsx");
    expect(mapPage).toContain("showDetailPanel={false}");
  });

  it("10. click en acción tabla activa geolocalizar/reubicar", () => {
    const view = read(`${SHARED}/MapaDomiciliosGeolocalizacionView.tsx`);
    const lista = read(`${SHARED}/components/MapaDomiciliosGeolocalizacionLista.tsx`);
    expect(view).toContain("onGeolocalizar={startGeolocalizar}");
    expect(view).toContain("onReubicar={startReubicar}");
    expect(lista).toContain("onGeolocalizar(item)");
    expect(lista).toContain("onReubicar(item)");
  });

  it("11. overlay no muestra ID al operador", () => {
    const mapa = read(`${SHARED}/components/MapaDomiciliosGeolocalizacionMapPanel.tsx`);
    const overlayBlock = mapa.slice(mapa.indexOf("editMode ?"), mapa.indexOf("<MapContainer"));
    expect(overlayBlock).not.toContain("#{");
    expect(overlayBlock).not.toContain("domicilio_id}");
    expect(overlayBlock).toContain("edit.searchText");
    expect(overlayBlock).toContain("Buscar");
    expect(overlayBlock).toContain("Guardar");
    expect(overlayBlock).toContain("Cerrar");
  });

  it("12. Limpiar borra búsqueda", () => {
    const hook = read(`${SHARED}/hooks/useGestionDomicilios.ts`);
    const view = read(`${SHARED}/MapaDomiciliosGeolocalizacionView.tsx`);
    expect(hook).toContain("clearSearch");
    expect(hook).toContain('setSearchInput("")');
    expect(hook).toContain('setAppliedQ("")');
    expect(view).toContain("onLimpiar={clearSearch}");
  });

  it("13. Filtrar llama getGestionDomicilios con q", () => {
    const hook = read(`${SHARED}/hooks/useGestionDomicilios.ts`);
    const view = read(`${SHARED}/MapaDomiciliosGeolocalizacionView.tsx`);
    expect(hook).toContain("applySearch");
    expect(hook).toContain("q: appliedQ || undefined");
    expect(hook).toContain("getGestionDomicilios");
    expect(view).toContain("onFiltrar={applySearch}");
  });

  it("14. Realizados sigue intacto", () => {
    const mapPage = read("src/Containers/Mapa/MapPage.tsx");
    expect(mapPage).toContain("loadRealizados");
    expect(mapPage).toContain("MapaFiltrosUnificados");
    expect(mapPage).toContain("PanelResumenOperativo");
    expect(mapPage).toContain("MapaCanvas");
    expect(mapPage).toContain('modo === "realizados"');
  });
});

describe("PR6C.14 mapeo subtabs documentado", () => {
  it("subtabs mapean a status_operativo del backend sin cambios", () => {
    const filters = read(`${SHARED}/mapaDomiciliosOperativoFilters.ts`);
    expect(filters).toContain('value: "requiere_accion", label: "Para revisar"');
    expect(filters).toContain('value: "geolocalizado", label: "En el mapa"');
    expect(filters).toContain('value: "manual", label: "Validados"');
    expect(filters).toContain('value: "todos", label: "Todos"');
  });
});
