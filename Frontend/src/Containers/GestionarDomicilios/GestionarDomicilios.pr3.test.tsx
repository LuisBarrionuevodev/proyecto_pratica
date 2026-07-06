/** @jsxImportSource react */
import { createTheme, ThemeProvider } from "@mui/material/styles";
import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { renderToStaticMarkup } from "react-dom/server";

import { GestionarDomiciliosPageHeader } from "./components/GestionarDomiciliosPageHeader";
import { DomicilioClasificacionChips } from "./components/DomicilioClasificacionChips";
import { DomicilioDetallePanel } from "./components/DomicilioDetallePanel";
import {
  labelGeocodeEstado,
  labelNomenclaturaEstado,
  labelScoreUnificado,
} from "./domicilioClasificacionLabels";
import {
  labelMatchStrategy,
  labelScoreBandWithStrategy,
  scoreDisplayWithStrategy,
} from "./domicilioMatchStrategyLabels";
import { labelPriorityBand, priorityBandFromScore } from "./domicilioPriorityLabels";
import { mergeSliceItems } from "./domicilioItemsMerge";
import {
  DOMICILIOS_GEO_MAP_SLICES,
  DOMICILIOS_SLICE_TABS,
  sliceSupportsGeoActions,
  sliceSupportsNomenclaturaEdit,
} from "./domicilioSliceTabs";
import {
  DOMICILIOS_VIEW_TABS,
  SLICES_FOR_VIEW,
} from "./domicilioViewTabs";
import {
  getDomicilioSliceEmptyMessage,
  getDomicilioViewEmptyMessage,
} from "./domicilioSliceEmptyStates";
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
    match_strategy: "exact_tokens",
    confidence_reason: "Coincidencia exacta por tokens",
    ...overrides,
  };
}

describe("PR6B domicilioViewTabs", () => {
  it("renderiza 4 tabs visibles: Para revisar, Mapa, Validados, Todos", () => {
    expect(DOMICILIOS_VIEW_TABS).toHaveLength(4);
    expect(DOMICILIOS_VIEW_TABS.map((t) => t.label)).toEqual([
      "Para revisar",
      "Mapa",
      "Validados",
      "Todos",
    ]);
  });

  it("Para revisar agrupa slices internos correctos", () => {
    expect(SLICES_FOR_VIEW.para_revisar).toEqual([
      "nomenclatura_pendiente",
      "geo_pendiente",
      "baja_confianza",
      "error",
    ]);
  });

  it("Mapa usa geo_pendiente, baja_confianza y error", () => {
    expect(SLICES_FOR_VIEW.mapa).toEqual(["geo_pendiente", "baja_confianza", "error"]);
  });

  it("Validados usa ok y validado_manual", () => {
    expect(SLICES_FOR_VIEW.validados).toEqual(["ok", "validado_manual"]);
  });

  it("mergeSliceItems une slices sin duplicar domicilio_id", () => {
    const a: DomicilioPendienteItem = sampleItem({ domicilio_id: 1, slice: "geo_pendiente" });
    const b: DomicilioPendienteItem = sampleItem({ domicilio_id: 2, slice: "error" });
    const dup: DomicilioPendienteItem = sampleItem({ domicilio_id: 1, slice: "baja_confianza" });
    const merged = mergeSliceItems(
      SLICES_FOR_VIEW.mapa,
      {
        geo_pendiente: [a],
        baja_confianza: [dup],
        error: [b],
      },
      "all"
    );
    expect(merged).toHaveLength(2);
    expect(merged.map((i) => i.domicilio_id).sort()).toEqual([1, 2]);
  });
});

describe("PR6B GestionarDomiciliosContainer", () => {
  it("container usa tabs visibles PR6B", () => {
    const container = read("src/Containers/GestionarDomicilios/GestionarDomiciliosContainer.tsx");
    expect(container).toContain("DOMICILIOS_VIEW_TABS");
    expect(container).toContain("TabMapaOperativoView");
    expect(container).toContain("TabParaRevisarTable");
    expect(container).toContain("DomicilioSliceFilterChips");
  });

  it("Mapa muestra vista operativa con mapa y panel detalle", () => {
    const mapa = read("src/Containers/GestionarDomicilios/components/TabMapaOperativoView.tsx");
    expect(mapa).toContain("DomicilioOperativoMap");
    expect(mapa).toContain("DomicilioDetallePanel");
    expect(mapa).toContain("retryGeo");
    expect(mapa).toContain("ManualMapPanel");
  });

  it("panel detalle muestra match_strategy y confidence_reason", () => {
    const html = render(
      <DomicilioDetallePanel
        item={sampleItem({
          match_strategy: "exact_tokens",
          confidence_reason: "Coincidencia exacta por tokens",
        })}
      />
    );
    expect(html).toContain("Tokens exactos");
    expect(html).toContain("Coincidencia exacta por tokens");
    expect(html).not.toContain("exact_tokens");
  });

  it("Re-geolocalizar y pin manual siguen disponibles en mapa", () => {
    const mapa = read("src/Containers/GestionarDomicilios/components/TabMapaOperativoView.tsx");
    const detalle = read("src/Containers/GestionarDomicilios/components/DomicilioDetallePanel.tsx");
    expect(mapa).toContain("retryGeo");
    expect(mapa).toContain("ManualMapPanel");
    expect(mapa).toContain("onSaveManualPoint");
    expect(detalle).toContain("Re-geolocalizar");
    expect(detalle).toContain("Pin manual");
  });
});

describe("PR UI domicilioSliceTabs legacy", () => {
  it("conserva 7 slices internos para filtros secundarios", () => {
    expect(DOMICILIOS_SLICE_TABS).toHaveLength(7);
  });

  it("solo nomenclatura_pendiente permite edición nomenclatura", () => {
    expect(sliceSupportsNomenclaturaEdit("nomenclatura_pendiente")).toBe(true);
    expect(sliceSupportsNomenclaturaEdit("geo_pendiente")).toBe(false);
  });

  it("mapa en geo_pendiente y no en nomenclatura_pendiente", () => {
    expect(sliceSupportsGeoActions("geo_pendiente")).toBe(true);
    expect(sliceSupportsGeoActions("nomenclatura_pendiente")).toBe(false);
    expect(DOMICILIOS_GEO_MAP_SLICES.has("all")).toBe(false);
  });
});

describe("PR UI useDomiciliosPendientes fetch por slice", () => {
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
    expect(src).toContain("mergeSliceItems");
  });

  it("reutiliza cache al volver a un slice ya cargado", () => {
    const src = read("src/Containers/GestionarDomicilios/hooks/useDomiciliosPendientes.ts");
    expect(src).toContain("cached?.key === filtersCacheKey");
  });

  it("no cambia endpoint ni payload", () => {
    const src = read("src/Containers/GestionarDomicilios/hooks/useDomiciliosPendientes.ts");
    expect(src).toContain('getMapPendientes({ ...baseParams(), slice })');
    expect(src).not.toContain("POST");
  });
});

describe("PR UI GestionarDomiciliosContainer header", () => {
  it("renderiza header Gestión de Domicilios", () => {
    const html = render(<GestionarDomiciliosPageHeader />);
    expect(html).toContain("Gestión de Domicilios");
    expect(html).toContain("Control de nomenclatura, geolocalización y calidad de datos");
  });
});

describe("PR6B columnas Para revisar", () => {
  it("columnas incluyen Match y Prioridad", () => {
    const src = read("src/Containers/GestionarDomicilios/components/domicilioGestionSharedColumns.tsx");
    expect(src).toContain("buildParaRevisarColumns");
    expect(src).toContain('header: "Match"');
    expect(src).toContain('header: "Prioridad"');
  });

  it("prioridad visual por score sin cambiar cálculo", () => {
    expect(priorityBandFromScore(40)).toBe("alta");
    expect(priorityBandFromScore(65)).toBe("media");
    expect(priorityBandFromScore(85)).toBe("baja");
    expect(labelPriorityBand("alta")).toBe("Alta");
  });
});

describe("PR UI columnas y chips", () => {
  it("chips muestran labels humanos, no enums crudos", () => {
    const html = render(
      <DomicilioClasificacionChips
        item={sampleItem({
          nomenclatura_estado: "NOMENCLATURA_REVISAR",
          geocode_estado: "GEOCODE_PENDIENTE",
          score_unificado: 42,
        })}
      />
    );
    expect(html).toContain("Revisar calle");
    expect(html).toContain("Sin geocode");
    expect(html).not.toContain("NOMENCLATURA_REVISAR");
    expect(html).not.toContain("GEOCODE_PENDIENTE");
  });

  it("labels helper mapean score a bandas humanas", () => {
    expect(labelNomenclaturaEstado("NOMENCLATURA_OK")).toBe("Nomenclatura OK");
    expect(labelGeocodeEstado("GEOCODE_ERROR")).toBe("Error geocode");
    expect(labelScoreUnificado(92)).toBe("OK");
    expect(labelScoreUnificado(75)).toBe("Revisar");
    expect(labelScoreUnificado(40)).toBe("Pendiente");
  });

  it("PR6A.1 muestra label humano de estrategia, no enum crudo", () => {
    expect(labelMatchStrategy("exact_tokens")).toBe("Tokens exactos");
    expect(labelMatchStrategy("token_containment", "Coincidencia ambigua")).toBe("Ambiguo");
    expect(labelMatchStrategy(null)).toBe("—");
  });

  it("PR6A.1 score visual interpreta estrategia fuerte vs fuzzy", () => {
    expect(labelScoreBandWithStrategy(65, "exact_tokens")).toBe("OK");
    expect(scoreDisplayWithStrategy(65, "fuzzy")).toBe("65 · Revisar");
  });
});

describe("PR UI empty states", () => {
  it("mensaje correcto por vista y slice", () => {
    expect(getDomicilioViewEmptyMessage("para_revisar")).toContain("revisión");
    expect(getDomicilioViewEmptyMessage("mapa")).toContain("mapa");
    expect(getDomicilioSliceEmptyMessage("nomenclatura_pendiente")).toContain(
      "pendientes de nomenclatura"
    );
  });

  it("tablas pasan emptyMessage al MRT", () => {
    const nom = read("src/Containers/GestionarDomicilios/components/TabNomenclaturaTable.tsx");
    const para = read("src/Containers/GestionarDomicilios/components/TabParaRevisarTable.tsx");
    expect(nom).toContain("renderEmptyRowsFallback");
    expect(para).toContain("emptyMessage");
  });
});

describe("PR UI acciones existentes", () => {
  it("acciones nomenclatura siguen en TabNomenclaturaTable", () => {
    const src = read("src/Containers/GestionarDomicilios/components/TabNomenclaturaTable.tsx");
    expect(src).toContain("onEditingRowSave");
    expect(src).toContain("buildNomenclaturaPayload");
  });

  it("acciones geocode siguen en TabParaRevisar y mapa", () => {
    const para = read("src/Containers/GestionarDomicilios/components/TabParaRevisarTable.tsx");
    expect(para).toContain("Geolocalizar");
    const mapa = read("src/Containers/GestionarDomicilios/components/TabMapaOperativoView.tsx");
    expect(mapa).toContain("ManualMapPanel");
  });
});
