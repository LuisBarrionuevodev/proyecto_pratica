import { describe, expect, it } from "vitest";

import type { IActuacionListItem } from "../../../api/actuacionesListApi";
import {
  MENSAJE_BLOQUEO_ACTA_DOCUMENTACION,
  MENSAJE_BLOQUEO_EXPEDIENTE_EDICION,
  detectBlockedActaClearAttempt,
  getActuacionEditableFields,
  resolveActuacionEditStart,
  tieneExpedienteBloqueoEdicion,
} from "./actuacionEditRules";

const baseRow = { id: 1 } as IActuacionListItem;

describe("actuacionEditRules — expediente", () => {
  it("detecta bloqueo por notificación con expediente", () => {
    expect(tieneExpedienteBloqueoEdicion({ ...baseRow, notificacion_editable: false })).toBe(true);
  });

  it("detecta bloqueo por comprobación con expediente", () => {
    expect(tieneExpedienteBloqueoEdicion({ ...baseRow, comprobacion_editable: false })).toBe(true);
  });

  it("permite edición sin expediente asociado", () => {
    expect(tieneExpedienteBloqueoEdicion(baseRow)).toBe(false);
    expect(resolveActuacionEditStart(baseRow)).toEqual({ allowed: true });
  });

  it("bloquea edición con mensaje estándar cuando hay expediente", () => {
    const result = resolveActuacionEditStart({ ...baseRow, comprobacion_editable: false });
    expect(result).toEqual({
      allowed: false,
      message: MENSAJE_BLOQUEO_EXPEDIENTE_EDICION,
    });
  });
});

describe("getActuacionEditableFields", () => {
  it("inspección normal permite editar contribuyente y domicilio", () => {
    const fields = getActuacionEditableFields({ ...baseRow, tipo_actuacion: "INSPECCION" });
    expect(fields.modoEdicion).toBe("normal");
    expect(fields.canEditContribuyente).toBe(true);
    expect(fields.canEditDomicilio).toBe(true);
    expect(fields.canEditNotificacion).toBe(true);
  });

  it("reinspección por notificación no permite editar contribuyente", () => {
    const fields = getActuacionEditableFields({
      ...baseRow,
      tipo_actuacion: "REINSPECCION",
      documentacion_contexto: { circuito: "REINSPECCION_NOTIFICACION", propia: {} },
    });
    expect(fields.modoEdicion).toBe("reinspeccion_notificacion");
    expect(fields.canEditContribuyente).toBe(false);
    expect(fields.canEditNotificacion).toBe(false);
    expect(fields.canEditActas).toBe(true);
  });

  it("ratificación de clausura no permite editar contribuyente ni domicilio", () => {
    const fields = getActuacionEditableFields({
      ...baseRow,
      tipo_actuacion: "RATIFICACION DE CLAUSURA",
    });
    expect(fields.modoEdicion).toBe("ratificacion");
    expect(fields.canEditContribuyente).toBe(false);
    expect(fields.canEditDomicilio).toBe(false);
  });

  it("ratificación de decomiso no permite editar contribuyente", () => {
    const fields = getActuacionEditableFields({
      ...baseRow,
      tipo_actuacion: "RATIFICACION_DECOMISO",
    });
    expect(fields.modoEdicion).toBe("ratificacion");
    expect(fields.canEditContribuyente).toBe(false);
  });

  it("verificar e informar no permite editar contribuyente", () => {
    const fields = getActuacionEditableFields({
      ...baseRow,
      tipo_actuacion: "VERIFICAR E INFORMAR",
    });
    expect(fields.modoEdicion).toBe("verificar_informar");
    expect(fields.canEditContribuyente).toBe(false);
    expect(fields.canEditDomicilio).toBe(false);
  });
});

describe("detectBlockedActaClearAttempt", () => {
  it("detecta borrado de acta de notificación bloqueada", () => {
    const baseline = {
      ...baseRow,
      notificacion_editable: false,
      acta_notificacion_num: "100",
    } as IActuacionListItem;
    const draft = { ...baseline, acta_notificacion_num: "" };
    expect(detectBlockedActaClearAttempt(draft, baseline)).toBe(MENSAJE_BLOQUEO_ACTA_DOCUMENTACION);
  });

  it("detecta borrado de acta de comprobación bloqueada", () => {
    const baseline = {
      ...baseRow,
      comprobacion_editable: false,
      acta_comprobacion_num: "200",
    } as IActuacionListItem;
    const draft = { ...baseline, acta_comprobacion_num: null };
    expect(detectBlockedActaClearAttempt(draft, baseline)).toBe(MENSAJE_BLOQUEO_ACTA_DOCUMENTACION);
  });
});
