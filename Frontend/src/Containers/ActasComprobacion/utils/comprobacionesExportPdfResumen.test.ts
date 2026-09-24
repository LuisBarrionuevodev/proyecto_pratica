import { describe, expect, it } from "vitest";

import type { ComprobacionExportRow } from "./comprobacionExportTypes";
import {
  computeComprobacionesPdfResumenRows,
  countConResultadoCumplimiento,
} from "./comprobacionesExportPdfResumen";

function baseRow(overrides: Partial<ComprobacionExportRow> = {}): ComprobacionExportRow {
  return {
    actuacionId: 1,
    comprobacionId: 10,
    exportSlice: "expediente",
    fechaActuacion: "2026-05-27",
    ordenTrabajo: "000001",
    actaComprobacionNum: "456",
    contribuyente: "Pérez Juan",
    documento: "",
    domicilio: "San Martín 100",
    calle: "San Martín",
    numero: "100",
    rubro: "Panadería",
    comprobacionMotivo: "Falta de habilitación",
    expedienteEnvioNumero: "",
    expedienteEnvioAnio: "",
    fechaExpedienteEnvio: "",
    oficioNumero: "",
    oficioAnio: "",
    fechaOficio: "",
    causa: "",
    juzgado: "",
    expedienteRespuestaNumero: "",
    expedienteRespuestaAnio: "",
    fechaExpedienteRespuesta: "",
    resultadoCumplimiento: "",
    estadoRecorrido: "Pendiente expediente",
    reinspeccionEstado: "",
    inspectores: "",
    oficiosAgregados: "",
    expedientesAgregados: "",
    expedienteEnvioCompacto: "",
    oficiosNumeros: "",
    expedientesOficio: "",
    expedientesRespuesta: "",
    oficiosConRespuesta: "",
    causasAgregadas: "",
    juzgadosAgregados: "",
    estadoRecorridoVisitas: "",
    ...overrides,
  };
}

function valueFor(rows: ReturnType<typeof computeComprobacionesPdfResumenRows>, label: string): string {
  return rows.find((r) => r.indicator === label)?.value ?? "";
}

describe("comprobacionesExportPdfResumen", () => {
  it("cuenta actas del período sin duplicar", () => {
    const items = [baseRow(), baseRow({ actuacionId: 2, comprobacionId: 11 })];
    expect(valueFor(computeComprobacionesPdfResumenRows(items), "Actas de comprobación en el período")).toBe("2");
  });

  it("expediente, oficio y respuesta", () => {
    const items = [
      baseRow({ exportSlice: "oficio", expedienteEnvioNumero: "123", expedienteEnvioAnio: "2026" }),
      baseRow({
        actuacionId: 2,
        exportSlice: "recorrido",
        oficioNumero: "99",
        oficioAnio: "2026",
        expedienteRespuestaNumero: "456",
        expedienteRespuestaAnio: "2026",
      }),
    ];
    const resumen = computeComprobacionesPdfResumenRows(items);
    expect(valueFor(resumen, "Actas con expediente de envío")).toBe("1");
    expect(valueFor(resumen, "Actas con oficio")).toBe("1");
    expect(valueFor(resumen, "Actas con expediente de respuesta")).toBe("1");
  });

  it("cumplidas y pendientes por slice", () => {
    const items = [
      baseRow({ exportSlice: "expediente" }),
      baseRow({ actuacionId: 2, exportSlice: "oficio" }),
      baseRow({ actuacionId: 3, exportSlice: "recorrido", resultadoCumplimiento: "CUMPLE" }),
    ];
    const resumen = computeComprobacionesPdfResumenRows(items);
    expect(valueFor(resumen, "Actas cumplidas (CUMPLE)")).toBe("1");
    expect(valueFor(resumen, "Pendientes de expediente")).toBe("1");
    expect(valueFor(resumen, "Pendientes de oficio")).toBe("1");
    expect(countConResultadoCumplimiento(items)).toBe(1);
  });

  it("top motivo y rubro normalizados", () => {
    const items = [
      baseRow({ rubro: "Panadería", comprobacionMotivo: "Falta de habilitación" }),
      baseRow({ actuacionId: 2, rubro: "Panadería", comprobacionMotivo: "falta de habilitacion" }),
      baseRow({ actuacionId: 3, rubro: "Carnicería", comprobacionMotivo: "Otro" }),
    ];
    const resumen = computeComprobacionesPdfResumenRows(items);
    expect(valueFor(resumen, "Top motivo más frecuente")).toContain("FALTA DE HABILITACION");
    expect(valueFor(resumen, "Top rubro con más actas de comprobación")).toContain("PANADERIA");
  });

  it("excluye motivo PENDIENTE placeholder", () => {
    const items = [baseRow({ comprobacionMotivo: "PENDIENTE" })];
    expect(valueFor(computeComprobacionesPdfResumenRows(items), "Top motivo más frecuente")).toBe("—");
  });
});
