import { describe, expect, it } from "vitest";

import type { IComprobacionRecorridoRow } from "../../../api/actuacionesComprobacionActasApi";
import { mapRecorridoRow } from "./comprobacionesExportMappers";
import {
  buildComprobacionesNormalizedExcelRows,
  RECORRIDO_EXCEL_COLUMNS,
} from "./comprobacionesExportNormalizedRows";
import { buildComprobacionesVisualPdfRows } from "./comprobacionesExportVisualRows";
import {
  filtrarRecorridoPorEstadoReinspeccion,
  recFechaComprobacionChips,
  recOficioExpOtOrigenMotivosChips,
} from "./recorridoOficioExpLabels";

function row(overrides: Partial<IComprobacionRecorridoRow> = {}): IComprobacionRecorridoRow {
  return {
    id: 1,
    estado_recorrido: "—",
    fecha_actuacion: "2026-05-27",
    orden_trabajo_numero: "004693",
    acta_comprobacion_num: "009345",
    comprobacion_motivo: "Falta de Higiene",
    motivos_comprobacion: ["Falta de Higiene"],
    rubro_nombre: "Panadería",
    calle: "San Martín",
    numero: "100",
    contrib_apellido: "Pérez",
    contrib_nombre: "Juan",
    doc_nro: "30111222",
    ...overrides,
  };
}

const OFICIO_CON_CAUSA = {
  oficio_texto: "372/2026",
  expediente_texto: "013408/2026",
  causa: "1992833",
  tipo_iniciador: "VERIFICAR_INFORMAR_OFICIO",
  estado_iniciador: "CUMPLIDO",
  estado_ejecucion: "REALIZADO",
  resultado_cumplimiento_oficio: "CUMPLE",
};

const OFICIO_CUMPLE = {
  oficio_texto: "3489/2026",
  expediente_texto: "012388/2026",
  tipo_iniciador: "VERIFICAR_INFORMAR_OFICIO",
  estado_iniciador: "CUMPLIDO",
  estado_ejecucion: "REALIZADO",
  resultado_cumplimiento_oficio: "CUMPLE",
};

const OFICIO_NO_CUMPLE = {
  oficio_texto: "3490/2026",
  expediente_texto: "012389/2026",
  tipo_iniciador: "RATIFICACION_CLAUSURA_OFICIO",
  estado_iniciador: "CUMPLIDO",
  estado_ejecucion: "REALIZADO",
  resultado_cumplimiento_oficio: "NO_CUMPLE",
};

const OFICIO_CONTRA = {
  oficio_texto: "3500/2026",
  expediente_texto: "012400/2026",
  tipo_iniciador: "REINSPECCION_OFICIO",
  estado_iniciador: "PENDIENTE",
  estado_ejecucion: "NO_REALIZADO",
  resultado_cumplimiento_oficio: "NO_CUMPLE",
  conclusion: "No cumple",
  ejecucion_reinspeccion: {
    tipo_inspeccion_labrada: "REINSPECCION",
    orden_trabajo_numero: "08888",
    fecha_actuacion: "2026-07-20",
  },
};

describe("HOTFIX V1.1-RECORRIDO-COMP.1A", () => {
  it("1. caso con expediente de envío y causa", () => {
    const r = row({
      expediente_numero: "013151",
      expediente_anio: 2026,
      oficios_resumen: [OFICIO_CON_CAUSA],
    });
    expect(recFechaComprobacionChips(r)).toEqual([
      "2026-05-27",
      "Comp. 009345",
      "Exp. envío 013151/2026",
    ]);
    expect(recOficioExpOtOrigenMotivosChips(r)).toEqual([
      "Oficio 372/2026",
      "Exp. 013408/2026",
      "OT origen 004693",
      "Causa 1992833",
      "Falta de Higiene",
    ]);

    const mapped = mapRecorridoRow(r);
    const [pdf] = buildComprobacionesVisualPdfRows([mapped]);
    const [excel] = buildComprobacionesNormalizedExcelRows([mapped], "recorrido");
    expect(pdf.fechaComprobacion).toContain("Exp. envío 013151/2026");
    expect(pdf.oficioExpOtMotivos).toContain("Causa 1992833");
    expect(excel["Expediente de envío"]).toBe("013151/2026");
    expect(excel.Causa).toBe("1992833");
  });

  it("2. caso sin expediente de envío ni causa ni OT origen: sin placeholders", () => {
    const r = row({
      orden_trabajo_numero: null,
      oficios_resumen: [{ oficio_texto: "372/2026", expediente_texto: "013408/2026" }],
    });
    const fecha = recFechaComprobacionChips(r);
    expect(fecha).toEqual(["2026-05-27", "Comp. 009345"]);
    expect(fecha.join(" ")).not.toMatch(/envío/i);
    const oficio = recOficioExpOtOrigenMotivosChips(r);
    expect(oficio).toEqual(["Oficio 372/2026", "Exp. 013408/2026", "Falta de Higiene"]);
    expect(oficio.some((c) => /OT origen|Causa/i.test(c))).toBe(false);
    expect(oficio).not.toContain("—");

    const mapped = mapRecorridoRow(r);
    const [pdf] = buildComprobacionesVisualPdfRows([mapped]);
    const [excel] = buildComprobacionesNormalizedExcelRows([mapped], "recorrido");
    expect(pdf.fechaComprobacion).not.toMatch(/envío/i);
    expect(pdf.oficioExpOtMotivos).not.toMatch(/Causa/i);
    expect(excel["Expediente de envío"]).toBe("");
    expect(excel.Causa).toBe("");
  });

  it("3. Cumple y No cumple simple entran en Reinspección realizada", () => {
    const cumple = row({ id: 1, oficios_resumen: [OFICIO_CUMPLE] });
    const noCumple = row({ id: 2, oficios_resumen: [OFICIO_NO_CUMPLE] });
    const contra = row({ id: 3, oficios_resumen: [OFICIO_CONTRA] });
    const ids = filtrarRecorridoPorEstadoReinspeccion([cumple, noCumple, contra], "REALIZADA").map(
      (r) => r.id
    );
    expect(ids).toEqual([1, 2]);
  });

  it("4. pendiente inicial y pendiente por contraproducencia entran en Reinspección pendiente", () => {
    const inicial = row({ id: 10, oficios_resumen: [] });
    const contra = row({ id: 11, oficios_resumen: [OFICIO_CONTRA] });
    const cumple = row({ id: 12, oficios_resumen: [OFICIO_CUMPLE] });
    const ids = filtrarRecorridoPorEstadoReinspeccion([inicial, contra, cumple], "PENDIENTE").map(
      (r) => r.id
    );
    expect(ids).toEqual([10, 11]);
  });

  it("5. PDF/XLSX con filtro aplicado: mismos registros y mismos datos que la grilla", () => {
    const conEnvio = row({
      id: 1,
      expediente_numero: "013151",
      expediente_anio: 2026,
      oficios_resumen: [OFICIO_CON_CAUSA],
    });
    const contra = row({ id: 2, oficios_resumen: [OFICIO_CONTRA] });
    const filtradas = filtrarRecorridoPorEstadoReinspeccion([conEnvio, contra], "REALIZADA");
    expect(filtradas.map((r) => r.id)).toEqual([1]);

    const mapped = filtradas.map(mapRecorridoRow);
    const [pdf] = buildComprobacionesVisualPdfRows(mapped);
    const excel = buildComprobacionesNormalizedExcelRows(mapped, "recorrido");

    expect(excel).toHaveLength(1);
    expect(Object.keys(excel[0])).toEqual([...RECORRIDO_EXCEL_COLUMNS]);
    expect(excel[0]["Expediente de envío"]).toBe("013151/2026");
    expect(excel[0].Causa).toBe("1992833");
    expect(excel[0]["N.º oficio"]).toBe("372/2026");
    expect(pdf.fechaComprobacion).toContain("Exp. envío 013151/2026");
    expect(pdf.oficioExpOtMotivos).toContain("Oficio 372/2026");
    expect(pdf.oficioExpOtMotivos).toContain("Exp. 013408/2026");
    expect(pdf.oficioExpOtMotivos).toContain("OT origen 004693");
    expect(pdf.oficioExpOtMotivos).toContain("Causa 1992833");
    expect(pdf.oficioExpOtMotivos).toContain("Falta de Higiene");
  });
});
