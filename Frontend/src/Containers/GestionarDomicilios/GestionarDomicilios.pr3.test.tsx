/** @jsxImportSource react */
import { createTheme, ThemeProvider } from "@mui/material/styles";
import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { renderToStaticMarkup } from "react-dom/server";

import { DomicilioClasificacionChips } from "./components/DomicilioClasificacionChips";
import {
  DOMICILIOS_SLICE_TABS,
  sliceSupportsGeoActions,
  sliceSupportsNomenclaturaEdit,
} from "./domicilioSliceTabs";
import type { DomicilioPendienteItem } from "./types";

const read = (rel: string) => readFileSync(resolve(process.cwd(), rel), "utf8");
const theme = createTheme();

function render(ui: React.ReactElement) {
  return renderToStaticMarkup(<ThemeProvider theme={theme}>{ui}</ThemeProvider>);
}

function sampleItem(overrides: Partial<DomicilioPendienteItem> = {}): DomicilioPendienteItem {
  return {
    domicilio_id: 1,
    calle_raw: "monteagudo",
    calle_normalizada: "Dr Bernardo Monteagudo",
    numero_raw: "672",
    numero: "672",
    numero_tipo: "NUMERO",
    esquina_normalizada: null,
    calle_status: "OK",
    esquina_status: null,
    geo_status: "OK",
    error_msg: null,
    lat: -26.8,
    lng: -65.2,
    nomenclatura_estado: "NOMENCLATURA_OK",
    geocode_estado: "GEOCODE_OK",
    score_unificado: 95,
    slice: "ok",
    source: "AUTO",
    ...overrides,
  };
}

describe("PR3 domicilioSliceTabs", () => {
  it("define 7 tabs mapeadas a slice backend", () => {
    expect(DOMICILIOS_SLICE_TABS).toHaveLength(7);
    expect(DOMICILIOS_SLICE_TABS.map((t) => t.slice)).toEqual([
      "nomenclatura_pendiente",
      "geo_pendiente",
      "baja_confianza",
      "ok",
      "validado_manual",
      "error",
      "all",
    ]);
  });

  it("slice nomenclatura_pendiente mapea a query nomenclatura_pendiente", () => {
    expect(DOMICILIOS_SLICE_TABS[0].slice).toBe("nomenclatura_pendiente");
  });

  it("slice geo_pendiente mapea a query geo_pendiente", () => {
    expect(DOMICILIOS_SLICE_TABS[1].slice).toBe("geo_pendiente");
  });

  it("slice baja_confianza mapea a query baja_confianza", () => {
    expect(DOMICILIOS_SLICE_TABS[2].slice).toBe("baja_confianza");
  });

  it("solo nomenclatura_pendiente permite edición nomenclatura", () => {
    expect(sliceSupportsNomenclaturaEdit("nomenclatura_pendiente")).toBe(true);
    expect(sliceSupportsNomenclaturaEdit("geo_pendiente")).toBe(false);
  });

  it("slices geo-compatibles incluyen mapa manual", () => {
    expect(sliceSupportsGeoActions("geo_pendiente")).toBe(true);
    expect(sliceSupportsGeoActions("baja_confianza")).toBe(true);
    expect(sliceSupportsGeoActions("nomenclatura_pendiente")).toBe(false);
  });
});

describe("PR3 useDomiciliosPendientes fetch por slice", () => {
  it("hook usa slice= en getMapPendientes", () => {
    const src = read("src/Containers/GestionarDomicilios/hooks/useDomiciliosPendientes.ts");
    expect(src).toContain("getMapPendientes({ ...baseParams(), slice })");
    expect(src).not.toContain('kind: "norm"');
    expect(src).not.toContain('kind: "map"');
  });

  it("cache por slice con itemsBySliceRef y loadedSlicesRef", () => {
    const src = read("src/Containers/GestionarDomicilios/hooks/useDomiciliosPendientes.ts");
    expect(src).toContain("itemsBySliceRef");
    expect(src).toContain("loadedSlicesRef");
    expect(src).toContain("ensureSliceLoaded");
    expect(src).toContain("refreshActiveSlice");
  });

  it("reutiliza cache al volver a un slice ya cargado", () => {
    const src = read("src/Containers/GestionarDomicilios/hooks/useDomiciliosPendientes.ts");
    expect(src).toContain("cached?.key === filtersCacheKey");
  });
});

describe("PR3 GestionarDomiciliosContainer", () => {
  it("renderiza tabs nuevas por slice", () => {
    const container = read("src/Containers/GestionarDomicilios/GestionarDomiciliosContainer.tsx");
    const tabs = read("src/Containers/GestionarDomicilios/domicilioSliceTabs.ts");
    expect(container).toContain("DOMICILIOS_SLICE_TABS");
    expect(container).toContain("refreshActiveSlice");
    expect(tabs).toContain("Pendientes nomenclatura");
    expect(tabs).toContain("Baja confianza");
    expect(tabs).toContain("Validados manualmente");
  });

  it("tab nomenclatura usa TabNomenclaturaTable", () => {
    const src = read("src/Containers/GestionarDomicilios/GestionarDomiciliosContainer.tsx");
    expect(src).toContain("sliceSupportsNomenclaturaEdit");
    expect(src).toContain("TabNomenclaturaTable");
  });

  it("tab geo_pendiente usa TabGeolocalizacionTable y mapa", () => {
    const src = read("src/Containers/GestionarDomicilios/GestionarDomiciliosContainer.tsx");
    expect(src).toContain('activeSlice === "geo_pendiente"');
    expect(src).toContain("TabGeolocalizacionTable");
    expect(src).toContain("ManualMapPanel");
  });
});

describe("PR3 DomicilioClasificacionChips", () => {
  it("muestra score_unificado y estados compuestos", () => {
    const html = render(<DomicilioClasificacionChips item={sampleItem()} />);
    expect(html).toContain("NOMENCLATURA_OK");
    expect(html).toContain("GEOCODE_OK");
    expect(html).toContain("Score 95");
  });

  it("muestra nomenclatura_estado y geocode_estado en filas con clasificación", () => {
    const html = render(
      <DomicilioClasificacionChips
        item={sampleItem({
          nomenclatura_estado: "NOMENCLATURA_REVISAR",
          geocode_estado: "GEOCODE_PENDIENTE",
          score_unificado: 42,
        })}
      />
    );
    expect(html).toContain("NOMENCLATURA_REVISAR");
    expect(html).toContain("GEOCODE_PENDIENTE");
    expect(html).toContain("Score 42");
  });
});

describe("PR3 tablas compartidas", () => {
  it("TabNomenclaturaTable incluye columnas de clasificación", () => {
    const src = read("src/Containers/GestionarDomicilios/components/TabNomenclaturaTable.tsx");
    expect(src).toContain("buildDomicilioClasificacionColumns");
  });

  it("TabGeolocalizacionTable incluye columnas de clasificación", () => {
    const src = read("src/Containers/GestionarDomicilios/components/TabGeolocalizacionTable.tsx");
    expect(src).toContain("buildDomicilioClasificacionColumns");
  });

  it("acciones nomenclatura siguen en TabNomenclaturaTable", () => {
    const src = read("src/Containers/GestionarDomicilios/components/TabNomenclaturaTable.tsx");
    expect(src).toContain("onEditingRowSave");
    expect(src).toContain("buildNomenclaturaPayload");
  });

  it("acciones geocode siguen en TabGeolocalizacionTable", () => {
    const src = read("src/Containers/GestionarDomicilios/components/TabGeolocalizacionTable.tsx");
    expect(src).toContain("Geolocalizar");
    expect(src).toContain("onGeolocalizar");
  });
});
