import { describe, expect, it } from "vitest";

import type { IActuacionListItem } from "../../../api/actuacionesListApi";
import {
  computeActuacionesPdfResumenRows,
  isInspeccionIntegralOrDenuncia,
  isRatificacionClausura,
  isRatificacionDecomiso,
  isReinspeccionPorNotificacion,
  isReinspeccionPorOficio,
  kilosDecomisoPropios,
  tieneComprobacionLabrada,
  tieneNotificacionLabradaMotivos,
} from "./actuacionesExportPdfResumen";

function baseRow(overrides: Partial<IActuacionListItem> = {}): IActuacionListItem {
  return {
    id: 1,
    orden_trabajo_numero: "000001",
    fecha_actuacion: "2026-05-27",
    rubro_nombre: null,
    inspector1: null,
    inspector2: null,
    inspector3: null,
    calle: null,
    numero: null,
    doc_nro: null,
    contrib_apellido: null,
    contrib_nombre: null,
    tipo_actuacion: "INSPECCION",
    contraproducencia: null,
    acta_inspeccion_num: null,
    acta_notificacion_num: null,
    notificacion_motivo_1: null,
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
    ...overrides,
  };
}

function valueForIndicator(rows: ReturnType<typeof computeActuacionesPdfResumenRows>, label: string): number {
  const hit = rows.find((r) => r.indicator === label);
  return Number(hit?.value ?? 0);
}

describe("actuacionesExportPdfResumen", () => {
  it("INSPECCION suma en Inspección Integral o Denuncia", () => {
    const row = baseRow({ tipo_actuacion: "INSPECCION" });
    expect(isInspeccionIntegralOrDenuncia(row)).toBe(true);
    const resumen = computeActuacionesPdfResumenRows([row]);
    expect(valueForIndicator(resumen, "Inspección Integral o Denuncia")).toBe(1);
  });

  it("reinspección por notificación suma en su indicador", () => {
    const row = baseRow({
      tipo_actuacion: "REINSPECCION",
      documentacion_contexto: {
        circuito: "REINSPECCION_NOTIFICACION",
        propia: {},
      },
    });
    expect(isReinspeccionPorNotificacion(row)).toBe(true);
    expect(isReinspeccionPorOficio(row)).toBe(false);
    expect(valueForIndicator(computeActuacionesPdfResumenRows([row]), "Reinspecciones por Notificación")).toBe(1);
    expect(valueForIndicator(computeActuacionesPdfResumenRows([row]), "Reinspecciones por Oficio")).toBe(0);
  });

  it("reinspección por oficio (tipo REINSPECCION + origen oficio) suma en Reinspecciones por Oficio", () => {
    const row = baseRow({
      tipo_actuacion: "REINSPECCION",
      origen_reinspeccion_oficio: {
        comprobacion_acta_numero: "123456",
        comprobacion_acta_anio: 2026,
        oficio_numero: "99",
        oficio_anio: 2026,
      },
    });
    expect(isReinspeccionPorOficio(row)).toBe(true);
    expect(isReinspeccionPorNotificacion(row)).toBe(false);
    const resumen = computeActuacionesPdfResumenRows([row]);
    expect(valueForIndicator(resumen, "Reinspecciones por Oficio")).toBe(1);
    expect(valueForIndicator(resumen, "Reinspecciones por Notificación")).toBe(0);
  });

  it("ratificación de clausura y decomiso se cuentan por separado", () => {
    const clausura = baseRow({ tipo_actuacion: "RATIFICACION DE CLAUSURA" });
    const decomiso = baseRow({ tipo_actuacion: "Ratificación de decomiso" });
    expect(isRatificacionClausura(clausura)).toBe(true);
    expect(isRatificacionDecomiso(decomiso)).toBe(true);
    const resumen = computeActuacionesPdfResumenRows([clausura, decomiso]);
    expect(valueForIndicator(resumen, "Ratificaciones de clausura")).toBe(1);
    expect(valueForIndicator(resumen, "Ratificaciones de decomiso")).toBe(1);
  });

  it("acta de clausura propia no cuenta como ratificación", () => {
    const row = baseRow({
      tipo_actuacion: "INSPECCION",
      acta_clausura_num: "000111",
    });
    expect(isRatificacionClausura(row)).toBe(false);
    const resumen = computeActuacionesPdfResumenRows([row]);
    expect(valueForIndicator(resumen, "Actas de clausura")).toBe(1);
    expect(valueForIndicator(resumen, "Ratificaciones de clausura")).toBe(0);
  });

  it("reinspección con comprobación de origen no cuenta acta de comprobación labrada", () => {
    const row = baseRow({
      tipo_actuacion: "REINSPECCION",
      origen_reinspeccion_oficio: {
        comprobacion_acta_numero: "999999",
        comprobacion_acta_anio: 2025,
      },
      acta_comprobacion_num: null,
      comprobacion_motivo: null,
    });
    expect(tieneComprobacionLabrada(row)).toBe(false);
    expect(valueForIndicator(computeActuacionesPdfResumenRows([row]), "Actas de comprobación")).toBe(0);
    expect(valueForIndicator(computeActuacionesPdfResumenRows([row]), "Reinspecciones por Oficio")).toBe(1);
  });

  it("notificación previa sin acta/motivos propios no cuenta acta de notificación", () => {
    const row = baseRow({
      tipo_actuacion: "REINSPECCION",
      documentacion_contexto: { circuito: "REINSPECCION_NOTIFICACION", propia: {} },
      origen_reinspeccion_notificacion: { notificacion_acta_numero: "888888" },
      acta_notificacion_num: null,
      notificacion_motivo_1: null,
    });
    expect(tieneNotificacionLabradaMotivos(row)).toBe(false);
    expect(valueForIndicator(computeActuacionesPdfResumenRows([row]), "Actas de notificación")).toBe(0);
  });

  it("kilos solo si hay decomiso propio", () => {
    const conDecomiso = baseRow({ acta_decomiso_num: "000222", decomiso_kilos_total: 12.5 });
    const soloKg = baseRow({ decomiso_kilos_total: 99 });
    expect(kilosDecomisoPropios(conDecomiso)).toBe(12.5);
    expect(kilosDecomisoPropios(soloKg)).toBe(0);
    expect(valueForIndicator(computeActuacionesPdfResumenRows([conDecomiso]), "Mercadería decomisada (kg)")).toBe(
      12.5
    );
  });
});
