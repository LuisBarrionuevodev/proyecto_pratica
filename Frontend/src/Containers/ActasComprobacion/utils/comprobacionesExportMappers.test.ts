import { describe, expect, it } from "vitest";

import type { IComprobacionRecorridoRow } from "../../../api/actuacionesComprobacionActasApi";
import type { ComprobacionExportRow } from "./comprobacionExportTypes";
import {
  mapOficioPendienteRow,
  mapRecorridoRow,
  mapReinspeccionPendienteRow,
} from "./comprobacionesExportMappers";
import { buildComprobacionesNormalizedExcelRows } from "./comprobacionesExportNormalizedRows";
import { buildComprobacionesVisualPdfRows } from "./comprobacionesExportVisualRows";

function recorridoBase(overrides: Partial<IComprobacionRecorridoRow> = {}): IComprobacionRecorridoRow {
  return {
    id: 1,
    estado_recorrido: "Con oficio",
    fecha_actuacion: "2026-05-27",
    orden_trabajo_numero: "000001",
    acta_comprobacion_num: "456",
    comprobacion_motivo: "Falta de habilitación",
    rubro_nombre: "Panadería",
    calle: "San Martín",
    numero: "100",
    ...overrides,
  };
}

describe("DOCS-EXP.2 — comprobaciones export recorrido", () => {
  it("Excel recorrido incluye todos los oficios (columna compacta)", () => {
    const row = mapRecorridoRow(
      recorridoBase({
        oficios_resumen: [
          { numero_oficio: "3489", anio_oficio: 2026, numero_expediente: "012388", anio_expediente: 2026 },
          { numero_oficio: "3490", anio_oficio: 2026, numero_expediente: "012389", anio_expediente: 2026 },
        ],
      })
    );
    const [excel] = buildComprobacionesNormalizedExcelRows([row], "recorrido");
    expect(excel.Oficios).toBe("3489/2026 · 3490/2026");
    expect(excel["Expedientes de oficio"]).toBe("012388/2026 · 012389/2026");
  });

  it("PDF visual muestra todos los oficios y expedientes en recorrido", () => {
    const row = mapRecorridoRow(
      recorridoBase({
        oficios_resumen: [
          { numero_oficio: "3489", anio_oficio: 2026, numero_expediente: "012388", anio_expediente: 2026 },
          { numero_oficio: "3490", anio_oficio: 2026, numero_expediente: "012389", anio_expediente: 2026 },
        ],
      })
    );
    const [pdf] = buildComprobacionesVisualPdfRows([row]);
    expect(pdf.expedienteOficio).toContain("Oficio 3489/2026 · Oficio 3490/2026");
    expect(pdf.expedienteOficio).toContain("Exp. 012388/2026 · Exp. 012389/2026");
  });

  it("pendiente oficio mantiene formato legacy de columnas", () => {
    const row = mapOficioPendienteRow({
      id: 1,
      fecha_actuacion: "2026-05-27",
      orden_trabajo_numero: "000001",
      acta_comprobacion_num: "456",
      contrib_apellido: "Pérez",
      contrib_nombre: "Juan",
      calle: "San Martín",
      numero: "100",
      rubro_nombre: "Panadería",
      comprobacion_motivo: "Motivo",
      expediente_original_numero: "123",
      expediente_original_anio: "2026",
      expediente_original_fecha: "2026-05-01",
    } as Parameters<typeof mapOficioPendienteRow>[0]);
    const [excel] = buildComprobacionesNormalizedExcelRows([row], "oficio");
    expect(excel).toHaveProperty("Año");
    expect(excel).not.toHaveProperty("Oficios");
    expect(row.oficiosAgregados).toBe("");
  });

  it("pendiente reinspección mantiene oficio único sin agregados de recorrido", () => {
    const row = mapReinspeccionPendienteRow({
      id: 1,
      fecha_actuacion: "2026-05-27",
      orden_trabajo_numero: "000001",
      acta_comprobacion_num: "456",
      contrib_apellido: "Pérez",
      contrib_nombre: "Juan",
      calle: "San Martín",
      numero: "100",
      rubro_nombre: "Panadería",
      comprobacion_motivo: "Motivo",
      oficio_numero: "99",
      oficio_anio: 2026,
      estado_recorrido: "Pendiente",
    } as Parameters<typeof mapReinspeccionPendienteRow>[0]);
    const [pdf] = buildComprobacionesVisualPdfRows([row as ComprobacionExportRow]);
    expect(row.oficiosAgregados).toBe("");
    expect(pdf.expedienteOficio).toContain("Oficio 99/2026");
  });
});
