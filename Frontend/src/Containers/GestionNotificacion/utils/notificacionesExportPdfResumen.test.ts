import { describe, expect, it } from "vitest";

import type { IActuacionesPendientesItem } from "../../../api/actuacionesPendientesApi";
import {
  computeNotificacionesPdfResumenRows,
  countNotificacionesConPlazoInicial,
  countReinspeccionesConComprobacionPosterior,
  sumProrrogasOtorgadas,
} from "./notificacionesExportPdfResumen";

function baseRow(overrides: Partial<IActuacionesPendientesItem> = {}): IActuacionesPendientesItem {
  return {
    id: 1,
    orden_trabajo_numero: "000001",
    fecha_actuacion: "2026-05-27",
    rubro_nombre: "Panadería",
    inspector1: null,
    inspector2: null,
    inspector3: null,
    calle: "San Martín",
    numero: "100",
    doc_nro: null,
    contrib_apellido: "Pérez",
    contrib_nombre: "Juan",
    tipo_actuacion: "INSPECCION",
    contraproducencia: null,
    acta_inspeccion_num: null,
    acta_notificacion_num: "123",
    notificacion_motivo_1: "Falta de habilitación",
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
    source_type: "NOTIFICACION",
    dias_restantes: 6,
    plazos_otorgados: 1,
    documentacion_contexto: {
      circuito: "COMUN_NOTIFICACION",
      propia: { notificacion_plazo_dias: 10 },
    },
    ...overrides,
  };
}

function valueFor(rows: ReturnType<typeof computeNotificacionesPdfResumenRows>, label: string): string {
  return rows.find((r) => r.indicator === label)?.value ?? "";
}

describe("notificacionesExportPdfResumen", () => {
  it("cuenta notificaciones del período sin duplicar por motivos", () => {
    const items = [
      baseRow({ id: 1, notificacion_motivo_1: "A", notificacion_motivo_2: "B" }),
      baseRow({ id: 2, notificacion_motivo_1: "C" }),
    ];
    expect(valueFor(computeNotificacionesPdfResumenRows(items), "Notificaciones en el período")).toBe("2");
  });

  it("plazos iniciales y prórrogas", () => {
    const items = [
      baseRow({ plazos_otorgados: 2 }),
      baseRow({ id: 2, plazos_otorgados: 0, documentacion_contexto: { circuito: "COMUN_NOTIFICACION", propia: {} } }),
    ];
    expect(countNotificacionesConPlazoInicial(items)).toBe(1);
    expect(sumProrrogasOtorgadas(items)).toBe(2);
  });

  it("top rubro y motivo recurrente", () => {
    const items = [
      baseRow({ rubro_nombre: "Panadería", notificacion_motivo_1: "Falta de habilitación" }),
      baseRow({ id: 2, rubro_nombre: "Panadería", notificacion_motivo_1: "falta de habilitacion" }),
      baseRow({ id: 3, rubro_nombre: "Carnicería", notificacion_motivo_1: "Otro" }),
    ];
    const resumen = computeNotificacionesPdfResumenRows(items);
    expect(valueFor(resumen, "Top rubro con más notificaciones")).toContain("PANADERIA");
    expect(valueFor(resumen, "Motivo / infracción más recurrente")).toContain("FALTA DE HABILITACION");
  });

  it("reinspección con comprobación posterior usa comprobacion_posterior_acta_num", () => {
    const items = [baseRow({ comprobacion_posterior_acta_num: "456" })];
    expect(countReinspeccionesConComprobacionPosterior(items)).toBe(1);
    expect(valueFor(computeNotificacionesPdfResumenRows(items), "Reinspecciones con acta de comprobación posterior")).toBe(
      "1"
    );
  });
});
