import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

import {
  buildOperativaComprobacionFiltroPayloadForTab,
  operativaComprobacionOficioApiOpts,
  operativaComprobacionReinspeccionApiOpts,
  operativaComprobacionTieneFiltro,
} from "./utils/buildOperativaComprobacionFiltroPayload";
import { shouldResetOperativaFiltroOnTabChange } from "./utils/operativaComprobacionTabChange";

const pagePath = resolve(process.cwd(), "src/Containers/ActasComprobacion/ActasComprobacionPage.tsx");
const pageSrc = () => readFileSync(pagePath, "utf8");

describe("operativaComprobacionTabChange", () => {
  it("resetea al cambiar entre tabs operativos", () => {
    expect(shouldResetOperativaFiltroOnTabChange("expediente", "oficio")).toBe(true);
    expect(shouldResetOperativaFiltroOnTabChange("oficio", "reinspeccion")).toBe(true);
    expect(shouldResetOperativaFiltroOnTabChange("reinspeccion", "expediente")).toBe(true);
    expect(shouldResetOperativaFiltroOnTabChange("expediente", "expediente")).toBe(false);
    expect(shouldResetOperativaFiltroOnTabChange("expediente", "recorrido")).toBe(false);
    expect(shouldResetOperativaFiltroOnTabChange("recorrido", "oficio")).toBe(false);
  });
});

describe("buildOperativaComprobacionFiltroPayloadForTab", () => {
  const inputs = {
    desde: "2026-04-01",
    hasta: "2026-04-30",
    numeroComprobacion: "123",
    expedienteEnvioNumero: "456",
    numeroOficio: "O1",
    expedienteRespuestaNumero: "R2",
  };

  it("expediente solo envía campos base", () => {
    expect(buildOperativaComprobacionFiltroPayloadForTab("expediente", inputs)).toEqual({
      desde: "2026-04-01",
      hasta: "2026-04-30",
      numeroComprobacion: "123",
    });
  });

  it("oficio incluye expediente de envío", () => {
    expect(buildOperativaComprobacionFiltroPayloadForTab("oficio", inputs)).toEqual({
      desde: "2026-04-01",
      hasta: "2026-04-30",
      numeroComprobacion: "123",
      expedienteEnvioNumero: "456",
    });
  });

  it("reinspección incluye oficio y expediente respuesta", () => {
    expect(buildOperativaComprobacionFiltroPayloadForTab("reinspeccion", inputs)).toEqual({
      desde: "2026-04-01",
      hasta: "2026-04-30",
      numeroComprobacion: "123",
      numeroOficio: "O1",
      expedienteRespuestaNumero: "R2",
    });
  });

  it("API oficio no envía campos de reinspección", () => {
    const payload = buildOperativaComprobacionFiltroPayloadForTab("oficio", inputs);
    expect(operativaComprobacionOficioApiOpts(payload, false)).toEqual({
      omitirRangoFecha: true,
      numeroComprobacion: "123",
      expedienteEnvioNumero: "456",
    });
  });

  it("API reinspección no envía expediente de envío", () => {
    const payload = buildOperativaComprobacionFiltroPayloadForTab("reinspeccion", inputs);
    expect(operativaComprobacionReinspeccionApiOpts(payload, true)).toEqual({
      omitirRangoFecha: false,
      numeroComprobacion: "123",
      numeroOficio: "O1",
      expedienteRespuestaNumero: "R2",
    });
  });

  it("detecta filtros activos por tab", () => {
    expect(
      operativaComprobacionTieneFiltro("oficio", {
        desde: null,
        hasta: null,
        numeroComprobacion: null,
        expedienteEnvioNumero: "456",
      })
    ).toBe(true);
    expect(
      operativaComprobacionTieneFiltro("reinspeccion", {
        desde: null,
        hasta: null,
        numeroComprobacion: null,
        numeroOficio: "O1",
        expedienteRespuestaNumero: null,
      })
    ).toBe(true);
  });
});

function extractColumnsBlock(src: string, name: string): string {
  const start = src.indexOf(`const ${name} = useMemo`);
  if (start < 0) return "";
  const end = src.indexOf("const columns", start + 1);
  return end > start ? src.slice(start, end) : src.slice(start);
}

describe("ActasComprobacionPage UX.1 columnas", () => {
  it("expediente: Establecimiento sin Estado operativo", () => {
    const block = extractColumnsBlock(pageSrc(), "columnsExpediente");
    expect(block).toContain('header: "Establecimiento"');
    expect(block).toContain("BandejaEstablecimientoCell");
    expect(block).not.toContain("buildEstadoOperativoColumn");
  });

  it("oficio: sin columnas Estado / Estado operativo", () => {
    const block = extractColumnsBlock(pageSrc(), "columnsOficio");
    expect(block).not.toContain('id: "estado_doc"');
    expect(block).not.toContain("buildEstadoOperativoColumn");
  });

  it("reinspección: Titular, Oficio, sin Estado oficio ni Comprobación", () => {
    const s = pageSrc();
    expect(s).toContain('header: "Titular"');
    expect(s).toContain('header: "Oficio"');
    expect(s).toContain("reinOficioFilaChips");
    expect(s).not.toContain('id: "estado_oficio"');
    expect(s).not.toContain('header: "Comprobación"');
    expect(s).toMatch(/columnsRein[\s\S]*buildEstadoOperativoColumn/);
  });
});

describe("ActasComprobacionPage UX.1 reset tab", () => {
  it("integra shouldResetOperativaFiltroOnTabChange y limpia inputs", () => {
    const s = pageSrc();
    expect(s).toContain("shouldResetOperativaFiltroOnTabChange");
    expect(s).toContain("clearOperativaFiltroInputs");
    expect(s).toContain("setOpNumExpEnvio");
    expect(s).toContain("setOpNumOficio");
    expect(s).toContain("setOpNumExpRespuesta");
    expect(s).toContain("opAppliedRef.current = null");
  });
});
