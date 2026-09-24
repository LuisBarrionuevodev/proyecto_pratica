/** @jsxImportSource react */
import { createTheme, ThemeProvider } from "@mui/material/styles";
import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { renderToStaticMarkup } from "react-dom/server";

import type { GestionDomiciliosRow } from "../../api/gestionDomiciliosApi";
import { MapaDomicilioDetalleOperativo } from "../Mapa/views/MapaDomiciliosGeolocalizacion/components/MapaDomicilioDetalleOperativo";
import { labelGeoChip } from "../Mapa/views/MapaDomiciliosGeolocalizacion/mapaDomiciliosOperativoFilters";

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

describe("PR6C.6 vista compartida geolocalización", () => {
  it("no renderiza tabs antiguas", () => {
    const vista = read(`${SHARED}/MapaDomiciliosGeolocalizacionView.tsx`);
    expect(vista).not.toContain("DOMICILIOS_VIEW_TABS");
    expect(vista).not.toContain("TabParaRevisarTable");
    expect(vista).not.toContain("TabMapaOperativoView");
    expect(vista).not.toContain("DomicilioSliceFilterChips");
    expect(vista).toContain("MapaDomiciliosGeolocalizacionMapPanel");
  });

  it("llama getGestionDomicilios via useGestionDomicilios", () => {
    const hook = read(`${SHARED}/hooks/useGestionDomicilios.ts`);
    expect(hook).toContain("getGestionDomicilios");
    const vista = read(`${SHARED}/MapaDomiciliosGeolocalizacionView.tsx`);
    expect(vista).toContain("useGestionDomicilios");
    expect(vista).not.toContain("useDomiciliosPendientes");
    expect(vista).not.toContain("getMapPendientes");
  });

  it("no usa /map/pendientes?slice en la vista principal", () => {
    const vista = read(`${SHARED}/MapaDomiciliosGeolocalizacionView.tsx`);
    expect(vista).not.toContain("getMapPendientes");
    expect(vista).not.toContain("slice=");
    expect(vista).not.toContain("/map/pendientes");
  });

  it("layout mapa 65% + lista 35%", () => {
    const vista = read(`${SHARED}/MapaDomiciliosGeolocalizacionView.tsx`);
    expect(vista).toContain("MapaDomiciliosGeolocalizacionMapPanel");
    expect(vista).toContain("MapaDomiciliosGeolocalizacionLista");
    expect(vista).toContain("0 0 65%");
    expect(vista).toContain("0 0 35%");
  });

  it("filtro operativo sin slices visibles", () => {
    const filtro = read(`${SHARED}/mapaDomiciliosOperativoFilters.ts`);
    expect(filtro).toContain("Requieren acción");
    expect(filtro).toContain("Sin punto");
    expect(filtro).toContain("Punto dudoso");
    expect(filtro).toContain("Manuales");
    expect(filtro).toContain("Geolocalizados");
    expect(filtro).toContain("Todos");
    expect(filtro).not.toContain("nomenclatura_pendiente");
  });
});

describe("PR6C.6 chips EN MAPA / SIN COORDS", () => {
  it("labelGeoChip muestra texto operador", () => {
    expect(labelGeoChip("EN_MAPA")).toBe("EN MAPA");
    expect(labelGeoChip("SIN_COORDS")).toBe("SIN COORDS");
  });

  it("lista renderiza chip EN MAPA", () => {
    const lista = read(`${SHARED}/components/MapaDomiciliosGeolocalizacionLista.tsx`);
    expect(lista).toContain("labelGeoChip");
    expect(lista).toContain('geo_chip === "EN_MAPA"');
  });

  it("detalle operativo muestra chips humanos", () => {
    const html = render(
      <MapaDomicilioDetalleOperativo row={sampleRow({ geo_chip: "EN_MAPA", has_coordinates: true })} />
    );
    expect(html).toContain("EN MAPA");
    const sinCoords = render(
      <MapaDomicilioDetalleOperativo row={sampleRow({ geo_chip: "SIN_COORDS" })} />
    );
    expect(sinCoords).toContain("SIN COORDS");
  });
});

describe("PR6C.6 acciones Geolocalizar / Reubicar", () => {
  it("Geolocalizar activa overlay de edición en mapa principal", () => {
    const vista = read(`${SHARED}/MapaDomiciliosGeolocalizacionView.tsx`);
    expect(vista).toContain("startGeolocalizar");
    expect(vista).toContain("setManualEditRow");
    expect(vista).toContain("GESTION_MAP_DEFAULT_CENTER");
    expect(vista).toContain("editRow={manualEditRow}");
    expect(vista).not.toContain("ManualMapPanel");
  });

  it("Reubicar selecciona fila y enfoca coordenadas", () => {
    const vista = read(`${SHARED}/MapaDomiciliosGeolocalizacionView.tsx`);
    expect(vista).toContain("startReubicar");
    expect(vista).toContain("setFocusCenter");
    const mapa = read(`${SHARED}/components/MapaDomiciliosGeolocalizacionMapPanel.tsx`);
    expect(mapa).toContain("selectedIcon");
    expect(mapa).toContain("point.domicilio_id === selectedId");
  });

  it("lista muestra botones según geo_chip", () => {
    const lista = read(`${SHARED}/components/MapaDomiciliosGeolocalizacionLista.tsx`);
    expect(lista).toContain("Geolocalizar");
    expect(lista).toContain("Reubicar");
    expect(lista).toContain('item.geo_chip === "EN_MAPA"');
  });
});

describe("PR6C.6 guardar con confirmación y refresh parcial", () => {
  it("onGuardarPuntoManual usa guardarPuntoManual y refetch", () => {
    const vista = read(`${SHARED}/MapaDomiciliosGeolocalizacionView.tsx`);
    expect(vista).toContain("guardarPuntoManual");
    expect(vista).toContain("await refetch()");
    expect(vista).toContain('feedback.success("Ubicación guardada correctamente.")');
    expect(vista).not.toContain("window.location");
    expect(vista).not.toContain("location.reload");
  });

  it("mapa operativo confirma antes de guardar", () => {
    const mapa = read(`${SHARED}/components/MapaDomiciliosGeolocalizacionMapPanel.tsx`);
    expect(mapa).toContain("ConfirmarUbicacionDialog");
    expect(mapa).toContain("handleRequestSave");
    const hook = read(`${SHARED}/hooks/useMapaEdicionManual.ts`);
    expect(hook).toContain("shouldExecuteManualSave");
  });

  it("hook expone refetch parcial sin invalidar legacy pendientes", () => {
    const hook = read(`${SHARED}/hooks/useGestionDomicilios.ts`);
    expect(hook).toContain("const refetch");
    expect(hook).toContain("getGestionDomicilios(queryParams)");
    expect(hook).not.toContain("getMapPendientes");
  });
});

describe("PR6C.6 selección fila / mapa", () => {
  it("EN MAPA enfoca marcador vía focusCenter", () => {
    const vista = read(`${SHARED}/MapaDomiciliosGeolocalizacionView.tsx`);
    expect(vista).toContain('row.geo_chip === "EN_MAPA"');
    expect(vista).toContain("setFocusCenter([row.lat, row.lng])");
  });

  it("SIN COORDS enfoca SMT al seleccionar", () => {
    const vista = read(`${SHARED}/MapaDomiciliosGeolocalizacionView.tsx`);
    expect(vista).toContain("GESTION_MAP_DEFAULT_CENTER");
  });
});
