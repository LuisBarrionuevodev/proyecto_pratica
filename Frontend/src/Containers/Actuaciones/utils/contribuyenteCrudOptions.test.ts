import { describe, expect, it } from "vitest";
import type { IActuacionListItem } from "../../../api/actuacionesListApi";
import {
  applyContribuyenteClearFlag,
  applyExplicitContribuyenteClear,
  baselineTeniaContribuyente,
  buildGestionIdentidadPutFields,
  detectContribuyenteClearedByUser,
  identitySemanticChanged,
  mergeActuacionIdentidadFromApiRow,
  shouldPromptContribuyenteClear,
  stripGestionIdentidadResidualFromPut,
  tieneVinculoContribuyenteHidratado,
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
  it("detecta clear cuando baseline tenía contribuyente", () => {
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

  it("no infiere limpiar_contribuyente por inputs vacíos", () => {
    const original = baseRow();
    const draft = baseRow({
      doc_nro: null,
      contrib_apellido: null,
      contrib_nombre: null,
      razon_social: null,
    });
    expect(applyContribuyenteClearFlag(original, draft).limpiar_contribuyente).toBeUndefined();
    expect(buildGestionIdentidadPutFields(draft, original)).toEqual({});
  });

  it("no reinserta limpiar_contribuyente aunque el row lo traiga", () => {
    const original = baseRow();
    const draft = applyExplicitContribuyenteClear(baseRow());
    expect(buildGestionIdentidadPutFields(draft, original)).toEqual({});
  });

  it("identidad no tocada no entra al PUT", () => {
    const original = baseRow();
    const edited = baseRow({ observaciones_ejecucion: "nota" });
    expect(identitySemanticChanged(edited, original)).toBe(false);
    expect(buildGestionIdentidadPutFields(edited, original)).toEqual({});
    const stripped = stripGestionIdentidadResidualFromPut(edited);
    expect(stripped.doc_nro).toBeUndefined();
    expect(stripped.limpiar_contribuyente).toBeUndefined();
  });

  it("editar solo apellido conserva el resto de la baseline", () => {
    const original = baseRow();
    const edited = baseRow({ contrib_apellido: "Chávez" });
    expect(buildGestionIdentidadPutFields(edited, original)).toEqual({
      doc_nro: "30123456",
      contrib_apellido: "Chávez",
      contrib_nombre: "Juan",
      razon_social: null,
    });
  });

  it("hidratar nested contribuyente no cuenta como cambio", () => {
    const original = baseRow({
      contrib_apellido: null,
      contrib_nombre: null,
      contribuyente: { apellido: "Pérez", nombre: "Juan" },
    });
    expect(tieneVinculoContribuyenteHidratado(original)).toBe(true);
    expect(baselineTeniaContribuyente(original)).toBe(true);
    const hydrated = mergeActuacionIdentidadFromApiRow(original);
    expect(hydrated.contrib_apellido).toBe("Pérez");
    expect(buildGestionIdentidadPutFields(hydrated, original)).toEqual({});
  });

  it("vaciar todo con touch pide confirmación; cancelar no envía clear", () => {
    const original = baseRow();
    const emptied = baseRow({
      doc_nro: null,
      contrib_apellido: null,
      contrib_nombre: null,
      razon_social: null,
    });
    expect(
      shouldPromptContribuyenteClear(original, emptied, { contrib_apellido: true })
    ).toBe(true);
    expect(buildGestionIdentidadPutFields(emptied, original, { contrib_apellido: true })).toEqual(
      {}
    );
  });
});
