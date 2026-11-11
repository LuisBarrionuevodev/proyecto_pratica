import { describe, expect, it } from "vitest";

import type { IComprobacionRecorridoRow } from "../../../api/actuacionesComprobacionActasApi";
import { mapRecorridoRow } from "./comprobacionesExportMappers";
import {
  buildComprobacionesNormalizedExcelRows,
  RECORRIDO_EXCEL_COLUMNS,
} from "./comprobacionesExportNormalizedRows";
import { buildComprobacionesVisualPdfRows } from "./comprobacionesExportVisualRows";
import {
  recFechaComprobacionChips,
  recOficioExpOtOrigenMotivosChips,
  recorridoReinspeccionChips,
  recorridoSeguimientoOperativoChips,
} from "./recorridoOficioExpLabels";

function row(overrides: Partial<IComprobacionRecorridoRow> = {}): IComprobacionRecorridoRow {
  return {
    id: 1,
    estado_recorrido: "—",
    fecha_actuacion: "2026-05-27",
    orden_trabajo_numero: "000001",
    acta_comprobacion_num: "009345",
    comprobacion_motivo: "Falta de higiene",
    motivos_comprobacion: ["Falta de higiene"],
    rubro_nombre: "Panadería",
    calle: "San Martín",
    numero: "100",
    contrib_apellido: "Pérez",
    contrib_nombre: "Juan",
    doc_nro: "30111222",
    ...overrides,
  };
}

const OFICIO_CUMPLE = {
  oficio_texto: "3489/2026",
  expediente_texto: "012388/2026",
  tipo_iniciador: "VERIFICAR_INFORMAR_OFICIO",
  estado_iniciador: "CUMPLIDO",
  estado_ejecucion: "REALIZADO",
  resultado_cumplimiento_oficio: "CUMPLE",
  conclusion: "Cumple",
  fecha_conclusion: "2026-07-14",
  orden_trabajo_numero: "07696",
  ejecucion_reinspeccion: {
    tipo_inspeccion_labrada: "VERIFICAR E INFORMAR",
    orden_trabajo_numero: "07696",
    fecha_actuacion: "2026-07-14",
  },
};

const OFICIO_NO_CUMPLE = {
  oficio_texto: "3490/2026",
  expediente_texto: "012389/2026",
  tipo_iniciador: "RATIFICACION_CLAUSURA_OFICIO",
  estado_iniciador: "CUMPLIDO",
  estado_ejecucion: "REALIZADO",
  resultado_cumplimiento_oficio: "NO_CUMPLE",
  conclusion: "No cumple",
  fecha_conclusion: "2026-07-15",
  orden_trabajo_numero: "07697",
  ejecucion_reinspeccion: {
    tipo_inspeccion_labrada: "RATIFICACION DE CLAUSURA",
    orden_trabajo_numero: "07697",
    fecha_actuacion: "2026-07-15",
  },
};

const OFICIO_CONTRA = {
  oficio_texto: "3500/2026",
  expediente_texto: "012400/2026",
  tipo_iniciador: "REINSPECCION_OFICIO",
  estado_iniciador: "PENDIENTE",
  estado_ejecucion: "NO_REALIZADO",
  motivo_no_realizado: "LOCAL_CERRADO",
  resultado_cumplimiento_oficio: null,
  conclusion: "No cumple",
};

describe("V1.1-RECORRIDO-COMP.1 — grilla", () => {
  it("1. con OT de origen lo muestra en Oficio, no en Fecha", () => {
    const r = row({ oficios_resumen: [OFICIO_CUMPLE] });
    expect(recFechaComprobacionChips(r)).toEqual(["2026-05-27", "Comp. 009345"]);
    expect(recOficioExpOtOrigenMotivosChips(r)).toContain("OT origen 000001");
    expect(recOficioExpOtOrigenMotivosChips(r).join(" ")).not.toContain("07696");
  });

  it("2. carga solo actas no deja hueco de OT origen", () => {
    const r = row({ orden_trabajo_numero: null, oficios_resumen: [OFICIO_CUMPLE] });
    const chips = recOficioExpOtOrigenMotivosChips(r);
    expect(chips.some((c) => /^OT\b/.test(c))).toBe(false);
    expect(chips).toContain("Oficio 3489/2026");
    expect(chips).toContain("Exp. 012388/2026");
    expect(chips).toContain("Falta de higiene");
  });

  it("3. reinspección realizada Cumple", () => {
    const r = row({ oficios_resumen: [OFICIO_CUMPLE] });
    expect(recorridoReinspeccionChips(r)).toEqual(["Verificar e informar", "Cumple"]);
    expect(recorridoSeguimientoOperativoChips(r)).toEqual([
      "Reinspección realizada",
      "OT 07696",
      "Fecha 2026-07-14",
    ]);
  });

  it("4. reinspección realizada No cumple", () => {
    const r = row({ oficios_resumen: [OFICIO_NO_CUMPLE] });
    expect(recorridoReinspeccionChips(r)).toEqual(["Ratificación de clausura", "No cumple"]);
    expect(recorridoReinspeccionChips(r).join(" ")).not.toMatch(/(^| )Cumple/);
    expect(recorridoSeguimientoOperativoChips(r)).toEqual([
      "Reinspección realizada",
      "OT 07697",
      "Fecha 2026-07-15",
    ]);
  });

  it("5. No cumple con contraproducencia queda pendiente, sin conclusión final", () => {
    const r = row({ oficios_resumen: [OFICIO_CONTRA] });
    expect(recorridoReinspeccionChips(r)).toEqual(["Reinspección"]);
    expect(recorridoReinspeccionChips(r)).not.toContain("No cumple");
    expect(recorridoReinspeccionChips(r)).not.toContain("Cumple");
    expect(recorridoSeguimientoOperativoChips(r)).toEqual(["Pendiente de reinspección"]);
  });

  it("6. varios oficios no mezclan conclusiones ni duplican OT de visita en Oficio", () => {
    const r = row({ oficios_resumen: [OFICIO_CUMPLE, OFICIO_NO_CUMPLE] });
    const oficio = recOficioExpOtOrigenMotivosChips(r).join(" | ");
    expect(oficio).toContain("3489/2026");
    expect(oficio).toContain("3490/2026");
    expect(oficio).not.toContain("07696");
    expect(oficio).not.toContain("Conclusión");
    expect(recorridoReinspeccionChips(r)).toEqual([
      "3489/2026 · Verificar e informar",
      "Cumple",
      "3490/2026 · Ratificación de clausura",
      "No cumple",
    ]);
  });
});

describe("V1.1-RECORRIDO-COMP.1 — PDF y XLSX", () => {
  it("7. tabla, PDF y XLSX comparten datos sin OT ni conclusión duplicada", () => {
    const r = row({ oficios_resumen: [OFICIO_CUMPLE, OFICIO_NO_CUMPLE] });
    const mapped = mapRecorridoRow(r);
    const [pdf] = buildComprobacionesVisualPdfRows([mapped]);
    const excel = buildComprobacionesNormalizedExcelRows([mapped], "recorrido");

    expect(pdf.layout).toBe("recorrido");
    expect(pdf.fechaComprobacion).toContain("2026-05-27");
    expect(pdf.fechaComprobacion).toContain("Comp. 009345");
    expect(pdf.oficioExpOtMotivos).toContain("3489/2026");
    expect(pdf.oficioExpOtMotivos).toContain("OT origen 000001");
    expect(pdf.oficioExpOtMotivos).not.toContain("07696");
    expect(pdf.tipoConclusion).toContain("Cumple");
    expect(pdf.tipoConclusion).toContain("No cumple");
    expect(pdf.seguimientoOtFecha).toContain("Reinspección realizada");
    expect(pdf.seguimientoOtFecha).toContain("OT 07696");
    expect(pdf.seguimientoOtFecha.match(/Cumple/g) ?? []).toHaveLength(0);

    expect(excel).toHaveLength(2);
    expect(Object.keys(excel[0])).toEqual([...RECORRIDO_EXCEL_COLUMNS]);
    expect(excel[0]["OT origen"]).toBe("000001");
    expect(excel[0]["OT reinspección"]).toBe("07696");
    expect(excel[0]["Conclusión de reinspección"]).toBe("Cumple");
    expect(excel[1]["Conclusión de reinspección"]).toBe("No cumple");
    expect(excel[0]["N.º oficio"]).toBe("3489/2026");
    expect(excel[1]["N.º oficio"]).toBe("3490/2026");
    expect(excel.some((e) => String(e["OT origen"]) === "07696")).toBe(false);
  });

  it("solo actas: OT origen vacío en Excel, no —", () => {
    const r = row({ orden_trabajo_numero: null, oficios_resumen: [OFICIO_CUMPLE] });
    const [excel] = buildComprobacionesNormalizedExcelRows([mapRecorridoRow(r)], "recorrido");
    expect(excel["OT origen"]).toBe("");
    expect(excel["OT origen"]).not.toBe("—");
  });

  it("contra: Excel sin conclusión y seguimiento pendiente", () => {
    const r = row({ oficios_resumen: [OFICIO_CONTRA] });
    const [excel] = buildComprobacionesNormalizedExcelRows([mapRecorridoRow(r)], "recorrido");
    expect(excel["Conclusión de reinspección"]).toBe("");
    expect(excel.Seguimiento).toBe("Pendiente de reinspección");
  });
});
