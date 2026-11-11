import { describe, expect, it } from "vitest";

import type { IComprobacionRecorridoRow } from "../../../api/actuacionesComprobacionActasApi";
import { mapRecorridoRow } from "./comprobacionesExportMappers";
import {
  buildComprobacionesNormalizedExcelRows,
  RECORRIDO_EXCEL_COLUMNS,
} from "./comprobacionesExportNormalizedRows";
import { buildComprobacionesVisualPdfRows } from "./comprobacionesExportVisualRows";

function recorridoBase(overrides: Partial<IComprobacionRecorridoRow> = {}): IComprobacionRecorridoRow {
  return {
    id: 1,
    estado_recorrido: "Verificar e informar — visita realizada",
    fecha_actuacion: "2026-05-27",
    orden_trabajo_numero: "000001",
    acta_comprobacion_num: "456",
    comprobacion_motivo: "Falta de higiene",
    rubro_nombre: "Panadería",
    calle: "San Martín",
    numero: "100",
    expediente_numero: "66234",
    expediente_anio: 2026,
    ...overrides,
  };
}

describe("DOCS-EXP.3 — Excel recorrido compacto", () => {
  it("incluye todos los oficios y expedientes agregados", () => {
    const row = mapRecorridoRow(
      recorridoBase({
        oficios_resumen: [
          {
            oficio_texto: "432/2026",
            expediente_texto: "014578/2026",
            causa: "Falta de higiene",
            juzgado_nombre: "Juzgado X",
            visita_resumen_texto: "Oficio 432/2026 · Verificar e informar · Realizada",
          },
          {
            oficio_texto: "1989/2026",
            expediente_texto: "014543/2026",
            causa: "Falta de higiene",
            juzgado_nombre: "Juzgado X",
            visita_resumen_texto: "Oficio 1989/2026 · Ratificación de clausura · Realizada",
          },
        ],
      })
    );
    const excel = buildComprobacionesNormalizedExcelRows([row], "recorrido");

    expect(excel).toHaveLength(2);
    expect(excel[0]["N.º oficio"]).toBe("432/2026");
    expect(excel[1]["N.º oficio"]).toBe("1989/2026");
    expect(excel[0]["N.º expediente"]).toBe("014578/2026");
    expect(excel[1]["N.º expediente"]).toBe("014543/2026");
    expect(excel[0]["Motivos de comprobación"]).toBe("Falta de higiene");
    expect(excel[0].Seguimiento).toBe("Pendiente de reinspección");
  });

  it("no incluye columnas técnicas repetidas", () => {
    const row = mapRecorridoRow(recorridoBase());
    const [excel] = buildComprobacionesNormalizedExcelRows([row], "recorrido");
    const keys = Object.keys(excel);

    expect(keys).not.toContain("Año");
    expect(keys).not.toContain("Mes");
    expect(keys).not.toContain("Calle");
    expect(keys).not.toContain("Número");
    expect(keys).not.toContain("Actuación ID");
    expect(keys).not.toContain("Comprobación ID");
    expect(keys).toEqual([...RECORRIDO_EXCEL_COLUMNS]);
  });

  it("PDF no pierde múltiples oficios ni estado por visita", () => {
    const row = mapRecorridoRow(
      recorridoBase({
        oficios_resumen: [
          { oficio_texto: "432/2026", expediente_texto: "014578/2026", visita_resumen_texto: "Oficio 432/2026 · Verificar e informar · Realizada" },
          { oficio_texto: "1989/2026", expediente_texto: "014543/2026", visita_resumen_texto: "Oficio 1989/2026 · Ratificación de clausura · Realizada" },
        ],
      })
    );
    const [pdf] = buildComprobacionesVisualPdfRows([row]);
    expect(pdf.oficioExpOtMotivos).toContain("432/2026");
    expect(pdf.oficioExpOtMotivos).toContain("1989/2026");
    expect(pdf.seguimientoOtFecha).toContain("Pendiente de reinspección");
  });
});
