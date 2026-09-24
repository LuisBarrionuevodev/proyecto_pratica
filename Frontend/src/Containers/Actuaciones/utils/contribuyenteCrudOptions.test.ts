import { describe, expect, it } from "vitest";
import type { IActuacionListItem } from "../../../api/actuacionesListApi";
import {
  applyContribuyenteClearFlag,
  baselineTeniaContribuyente,
  detectContribuyenteClearedByUser,
} from "./contribuyenteCrudOptions";

const baseRow = (overrides: Partial<IActuacionListItem> = {}): IActuacionListItem =>
  ({
    id: 1,
    orden_trabajo_numero: "000001",
    fecha_actuacion: "2026-06-10",
    rubro_nombre: "Bar",
    inspector1: "A",
    inspector2: null,
    inspector3: null,
    calle: "San Martín",
    numero: "100",
    tipo_actuacion: "INSPECCION",
    contraproducencia: null,
    doc_nro: "30123456",
    contrib_apellido: "Pérez",
    contrib_nombre: "Juan",
    razon_social: null,
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
  }) as IActuacionListItem;

describe("contribuyenteCrudOptions", () => {
  it("detecta clear explícito cuando baseline tenía contribuyente", () => {
    const original = baseRow();
    const draft = baseRow({
      doc_nro: null,
      contrib_apellido: null,
      contrib_nombre: null,
      razon_social: null,
    });
    expect(detectContribuyenteClearedByUser(original, draft)).toBe(true);
  });

  it("no marca clear si baseline no tenía contribuyente", () => {
    const original = baseRow({
      doc_nro: null,
      contrib_apellido: null,
      contrib_nombre: null,
    });
    const draft = baseRow({
      doc_nro: null,
      contrib_apellido: null,
      contrib_nombre: null,
    });
    expect(baselineTeniaContribuyente(original)).toBe(false);
    expect(applyContribuyenteClearFlag(original, draft).limpiar_contribuyente).toBeUndefined();
  });

  it("no marca clear si solo cambian inspectores", () => {
    const original = baseRow();
    const draft = baseRow({ inspector1: "B", inspector2: "C" });
    expect(applyContribuyenteClearFlag(original, draft).limpiar_contribuyente).toBeUndefined();
  });

  it("aplica flag limpiar_contribuyente", () => {
    const original = baseRow();
    const draft = baseRow({
      doc_nro: null,
      contrib_apellido: null,
      contrib_nombre: null,
      razon_social: null,
    });
    const out = applyContribuyenteClearFlag(original, draft);
    expect(out.limpiar_contribuyente).toBe(true);
    expect(out.doc_nro).toBeNull();
  });
});
