import { describe, expect, it } from "vitest";

import type { IActuacionesPendientesItem } from "../../../api/actuacionesPendientesApi";
import { buildNotificacionesNormalizedExcelRows } from "./notificacionesExportNormalizedRows";
import { buildNotificacionesVisualPdfRows } from "./notificacionesExportVisualRows";
import {
  esFilaReinspeccionPorNotificacion,
  notificacionExportPdfText,
  notificacionOrigenActaText,
} from "./notificacionesExportShared";

function baseRow(overrides: Partial<IActuacionesPendientesItem> = {}): IActuacionesPendientesItem {
  return {
    id: 1,
    orden_trabajo_numero: "000001",
    fecha_actuacion: "2026-05-27",
    rubro_nombre: null,
    inspector1: null,
    inspector2: null,
    inspector3: null,
    calle: "San Martín",
    numero: "100",
    doc_nro: null,
    contrib_apellido: null,
    contrib_nombre: null,
    tipo_actuacion: "INSPECCION",
    contraproducencia: null,
    acta_inspeccion_num: null,
    acta_notificacion_num: "123",
    notificacion_motivo_1: "Motivo",
    notificacion_motivo_2: null,
    notificacion_motivo_3: null,
    acta_comprobacion_num: null,
    comprobacion_motivo: null,
    acta_clausura_num: null,
    acta_decomiso_num: null,
    decomiso_kilos_total: null,
    expediente_numero: null,
    expediente_anio: null,
    oficio_numero: null,
    oficio_anio: null,
    oficio_causa: null,
    documentacion_contexto: { circuito: "COMUN_NOTIFICACION", propia: {} },
    ...overrides,
  };
}

describe("DOCS-EXP.5 — notificación origen en export", () => {
  it("PDF visual de reinspección muestra Notif. origen con número/año", () => {
    const row = baseRow({
      tipo_actuacion: "REINSPECCION",
      acta_notificacion_num: "456",
      fecha_actuacion: "2026-06-10",
      documentacion_contexto: { circuito: "REINSPECCION_NOTIFICACION", propia: {} },
      origen_reinspeccion_notificacion: {
        notificacion_acta_numero: "123",
        notificacion_acta_anio: 2026,
      },
    });
    const [pdfRow] = buildNotificacionesVisualPdfRows([row]);
    expect(pdfRow.notificacion).toContain("Notif. origen: 123/2026");
    expect(pdfRow.notificacion).toContain("Acta notif.: 456/2026");
    expect(esFilaReinspeccionPorNotificacion(row)).toBe(true);
  });

  it("fila común sin origen no muestra Notif. origen", () => {
    const row = baseRow();
    expect(notificacionExportPdfText(row)).toBe("Notif. 123/2026");
    expect(notificacionExportPdfText(row)).not.toContain("Notif. origen");
    const [pdfRow] = buildNotificacionesVisualPdfRows([row]);
    expect(pdfRow.notificacion).not.toContain("Notif. origen");
  });

  it("diferencia acta propia y origen sin duplicar cuando son iguales", () => {
    const row = baseRow({
      documentacion_contexto: { circuito: "REINSPECCION_NOTIFICACION", propia: {} },
      origen_reinspeccion_notificacion: {
        notificacion_acta_numero: "123",
        notificacion_acta_anio: 2026,
      },
      acta_notificacion_num: "123",
      fecha_actuacion: "2026-05-27",
    });
    const texto = notificacionExportPdfText(row);
    expect(texto).toBe("Notif. origen: 123/2026");
    expect(texto).not.toContain("Acta notif.");
  });

  it("Excel incluye columna Notificación origen solo con dato de origen", () => {
    const conOrigen = baseRow({
      documentacion_contexto: { circuito: "REINSPECCION_NOTIFICACION", propia: {} },
      origen_reinspeccion_notificacion: {
        notificacion_acta_numero: "123",
        notificacion_acta_anio: 2026,
      },
    });
    const sinOrigen = baseRow();
    const [rowCon, rowSin] = buildNotificacionesNormalizedExcelRows(
      [conOrigen, sinOrigen],
      "total"
    );
    expect(rowCon["Notificación origen"]).toBe("123/2026");
    expect(rowSin["Notificación origen"]).toBe("");
    expect(notificacionOrigenActaText(sinOrigen)).toBe("");
  });
});
