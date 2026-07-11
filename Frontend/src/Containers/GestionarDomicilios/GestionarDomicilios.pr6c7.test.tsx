/** @jsxImportSource react */

import { createTheme, ThemeProvider } from "@mui/material/styles";

import { describe, expect, it } from "vitest";

import { readFileSync } from "node:fs";

import { resolve } from "node:path";

import { renderToStaticMarkup } from "react-dom/server";



import type { GestionDomiciliosRow } from "../../api/gestionDomiciliosApi";

import {

  CONFIRMAR_UBICACION_MENSAJE,

  CONFIRMAR_UBICACION_SECUNDARIO,

  CONFIRMAR_UBICACION_TITULO,

} from "../Mapa/views/MapaDomiciliosGeolocalizacion/components/ConfirmarUbicacionDialog";

import { MapaDomicilioDetalleOperativo } from "../Mapa/views/MapaDomiciliosGeolocalizacion/components/MapaDomicilioDetalleOperativo";

import {

  formatGestionDomiciliosSummaryLine,

  labelGeoChip,

} from "../Mapa/views/MapaDomiciliosGeolocalizacion/mapaDomiciliosOperativoFilters";

import { GESTION_DOMICILIOS_SEARCH_DEBOUNCE_MS } from "../Mapa/views/MapaDomiciliosGeolocalizacion/hooks/useGestionDomicilios";

import {

  createPendingManualSave,

  shouldExecuteManualSave,

} from "../Mapa/views/MapaDomiciliosGeolocalizacion/services/manualMapPanelSaveFlow";



const SHARED = "src/Containers/Mapa/views/MapaDomiciliosGeolocalizacion";

const read = (rel: string) => readFileSync(resolve(process.cwd(), rel), "utf8");

const theme = createTheme();



function render(ui: React.ReactElement) {

  return renderToStaticMarkup(<ThemeProvider theme={theme}>{ui}</ThemeProvider>);

}



function sampleRow(overrides: Partial<GestionDomiciliosRow> = {}): GestionDomiciliosRow {

  return {

    domicilio_id: 1,

    domicilio_linea: "San Martín 1009",

    status_operativo: "sin_punto",

    status_operativo_label: "Sin punto",

    geo_chip: "SIN_COORDS",

    has_coordinates: false,

    lat: null,

    lng: null,

    requiere_accion: true,

    ...overrides,

  };

}



describe("PR6C.7 buscador único superior", () => {

  it("renderiza buscador único en filtro superior", () => {

    const filtro = read(`${SHARED}/components/MapaDomiciliosGeolocalizacionFiltro.tsx`);

    expect(filtro).toContain('label="Buscar domicilio"');

    expect(filtro).not.toContain("enableGlobalFilter");

  });



  it("hook debouncea búsqueda y envía q al endpoint", () => {

    const hook = read(`${SHARED}/hooks/useGestionDomicilios.ts`);

    expect(hook).toContain("GESTION_DOMICILIOS_SEARCH_DEBOUNCE_MS");

    expect(hook).toContain("appliedQ");

    expect(hook).toContain("q: appliedQ");

    expect(hook).toContain("applySearch");

    expect(hook).toContain("setPage(1)");

    expect(GESTION_DOMICILIOS_SEARCH_DEBOUNCE_MS).toBeGreaterThanOrEqual(300);

    expect(GESTION_DOMICILIOS_SEARCH_DEBOUNCE_MS).toBeLessThanOrEqual(500);

  });



  it("lista no usa global filter interno de MRT", () => {

    const lista = read(`${SHARED}/components/MapaDomiciliosGeolocalizacionLista.tsx`);

    const base = read(`${SHARED}/mapaDomiciliosMrtGlassBase.ts`);

    expect(lista).toContain("enableGlobalFilter: false");

    expect(base).toContain("enableTopToolbar: false");

    expect(base).toContain("enableColumnFilters: false");

    expect(base).toContain("enableHiding: false");

    expect(base).toContain("enableDensityToggle: false");

  });

});



describe("PR6C.7 tabla limpia y acciones", () => {

  it("columnas mínimas Domicilio / Estado / Acción", () => {

    const lista = read(`${SHARED}/components/MapaDomiciliosGeolocalizacionLista.tsx`);

    expect(lista).toContain('header: "Domicilio"');

    expect(lista).toContain('header: "Estado"');

    expect(lista).toContain('header: "Acción"');

  });



  it("fila con coords muestra chip EN MAPA y Reubicar", () => {

    const lista = read(`${SHARED}/components/MapaDomiciliosGeolocalizacionLista.tsx`);

    expect(lista).toContain("labelGeoChip");

    expect(lista).toContain('"EN_MAPA"');

    expect(lista).toContain("Reubicar");

    expect(labelGeoChip("EN_MAPA")).toBe("EN MAPA");

  });



  it("fila sin coords muestra chip SIN COORDS y Geolocalizar", () => {

    const lista = read(`${SHARED}/components/MapaDomiciliosGeolocalizacionLista.tsx`);

    expect(lista).toContain("Geolocalizar");

    expect(labelGeoChip("SIN_COORDS")).toBe("SIN COORDS");

    const html = render(

      <MapaDomicilioDetalleOperativo

        row={sampleRow()}

        onGeolocalizar={() => {}}

      />

    );

    expect(html).toContain("SIN COORDS");

    expect(html).toContain("Geolocalizar");

  });

});



describe("PR6C.7 geolocalizar sin achicar mapa", () => {

  it("vista no renderiza ManualMapPanel ni segundo MapContainer", () => {

    const vista = read(`${SHARED}/MapaDomiciliosGeolocalizacionView.tsx`);

    expect(vista).not.toContain("ManualMapPanel");

    expect(vista).toContain("editRow={manualEditRow}");

    expect(vista).toContain("onSavePoint={onGuardarPuntoManual}");

  });



  it("mapa mantiene tamaño y muestra overlay de búsqueda", () => {

    const mapa = read(`${SHARED}/components/MapaDomiciliosGeolocalizacionMapPanel.tsx`);

    const vista = read(`${SHARED}/MapaDomiciliosGeolocalizacionView.tsx`);

    expect(mapa).toContain('label="Domicilio"');

    expect(mapa).toContain("Buscar");

    expect(mapa).toContain("mapEditOverlayGlassSx");

    expect(vista).toContain("MAP_GEO_PANEL_HEIGHT");

    expect(vista).not.toContain("ManualMapPanel");

    expect(mapa).toContain("<MapContainer");

  });



  it("Geolocalizar enfoca SMT y Reubicar usa coords actuales", () => {

    const vista = read(`${SHARED}/MapaDomiciliosGeolocalizacionView.tsx`);

    expect(vista).toContain("GESTION_MAP_DEFAULT_CENTER");

    expect(vista).toContain("setFocusCenter([row.lat, row.lng])");

  });

});



describe("PR6C.7 confirmación y guardado", () => {

  it("confirmación tiene título y textos correctos", () => {

    expect(CONFIRMAR_UBICACION_TITULO).toBe("Confirmar ubicación");

    expect(CONFIRMAR_UBICACION_MENSAJE).toBe(

      "¿Confirmás esta ubicación para el domicilio seleccionado?"

    );

    expect(CONFIRMAR_UBICACION_SECUNDARIO).toBe(

      "Se guardará este punto como ubicación del domicilio."

    );

    const dialog = read(`${SHARED}/components/ConfirmarUbicacionDialog.tsx`);

    expect(dialog).not.toContain("toFixed");

    expect(dialog).not.toContain("lat");

  });



  it("cancelar no guarda y confirmar sí", () => {

    const pending = createPendingManualSave(10, { lat: -26.8, lng: -65.2 });

    expect(shouldExecuteManualSave(false, pending)).toBe(false);

    expect(shouldExecuteManualSave(true, pending)).toBe(true);

  });



  it("guardar usa toast estándar y refetch parcial", () => {

    const vista = read(`${SHARED}/MapaDomiciliosGeolocalizacionView.tsx`);

    expect(vista).toContain('feedback.success("Ubicación guardada correctamente.")');

    expect(vista).toContain("await refetch()");

    expect(vista).not.toContain("location.reload");

    expect(vista).toContain("setManualEditRow(null)");

  });

});



describe("PR6C.7 contadores y header", () => {

  it("summary compacto desde totales globales", () => {

    const line = formatGestionDomiciliosSummaryLine({

      requieren_accion: 589,

      sin_punto: 580,

      geolocalizados: 111,

    });

    expect(line).toBe("589 requieren acción · 580 sin punto · 111 en mapa");

    const filtro = read(`${SHARED}/components/MapaDomiciliosGeolocalizacionFiltro.tsx`);

    expect(filtro).toContain("formatGestionDomiciliosSummaryLine");

    expect(filtro).toContain("Typography variant=\"caption\"");

  });



  it("header sin párrafo largo (props configurables)", () => {

    const header = read(`${SHARED}/components/MapaDomiciliosGeolocalizacionPageHeader.tsx`);

    expect(header).toContain("title");

    expect(header).toContain("subtitle");

    expect(header).not.toContain("revisá pendientes");

  });



  it("filtro operativo sigue disponible", () => {

    const filtro = read(`${SHARED}/mapaDomiciliosOperativoFilters.ts`);

    expect(filtro).toContain("MAPA_DOMICILIOS_SUBTABS");

    expect(filtro).toContain("Para revisar");

    expect(filtro).toContain("Todos");

  });

});

