import { describe, expect, it } from "vitest";

import type { IActuacionListItem } from "../../../api/actuacionesListApi";
import {
  MENSAJE_BLOQUEO_ACTA_DOCUMENTACION,
  MENSAJE_BLOQUEO_EXPEDIENTE_EDICION,
  detectBlockedActaClearAttempt,
  getActuacionEditableFields,
  resolveActuacionEditStart,
  resolveActuacionModoEdicion,
  tieneExpedienteBloqueoEdicion,
} from "./actuacionEditRules";

const baseRow = { id: 1 } as IActuacionListItem;

describe("actuacionEditRules ÿÿÿ expediente", () => {
  it("detecta bloqueo por notificaci?n con expediente", () => {
    expect(tieneExpedienteBloqueoEdicion({ ...baseRow, notificacion_editable: false })).toBe(true);
  });

  it("detecta bloqueo por comprobaci?n con expediente", () => {
    expect(tieneExpedienteBloqueoEdicion({ ...baseRow, comprobacion_editable: false })).toBe(true);
  });

  it("permite edición sin expediente asociado", () => {
    expect(tieneExpedienteBloqueoEdicion(baseRow)).toBe(false);
    expect(resolveActuacionEditStart(baseRow)).toEqual({ allowed: true });
  });

  it("permite edición cuando solo el acta tiene expediente (FIX.10A)", () => {
    expect(
      resolveActuacionEditStart({ ...baseRow, comprobacion_editable: false })
    ).toEqual({ allowed: true });
    expect(
      resolveActuacionEditStart({ ...baseRow, notificacion_editable: false })
    ).toEqual({ allowed: true });
  });

  it("bloquea edición solo con actuacion_bloqueada_por_expediente", () => {
    const result = resolveActuacionEditStart({
      ...baseRow,
      actuacion_bloqueada_por_expediente: true,
    });
    expect(result).toEqual({
      allowed: false,
      message: MENSAJE_BLOQUEO_EXPEDIENTE_EDICION,
    });
  });
});

describe("getActuacionEditableFields", () => {
  it("inspeccion normal sin flag backend usa fallback editable", () => {
    const fields = getActuacionEditableFields({ ...baseRow, tipo_actuacion: "INSPECCION" });
    expect(fields.modoEdicion).toBe("normal");
    expect(fields.canEditContribuyente).toBe(true);
    expect(fields.canEditDomicilio).toBe(true);
    expect(fields.canEditNotificacion).toBe(true);
  });

  it("reinspeccion por notificacion bloquea domicilio con flag backend", () => {
    const fields = getActuacionEditableFields({
      ...baseRow,
      tipo_actuacion: "REINSPECCION",
      can_edit_domicilio: false,
      domicilio_edit_blocked_reason:
        "La actuaci?n proviene de una reinspecci?n y el domicilio no puede modificarse.",
      documentacion_contexto: { circuito: "REINSPECCION_NOTIFICACION", propia: {} },
    });
    expect(fields.modoEdicion).toBe("reinspeccion_notificacion");
    expect(fields.canEditContribuyente).toBe(false);
    expect(fields.canEditDomicilio).toBe(false);
    expect(fields.domicilioEditBlockedReason).toContain("reinspecci?n");
    expect(fields.canEditNotificacion).toBe(false);
    expect(fields.canEditActas).toBe(true);
  });

  it("actuacion base de relevamiento habilita domicilio con flag backend", () => {
    const fields = getActuacionEditableFields({
      ...baseRow,
      tipo_actuacion: "INSPECCION",
      can_edit_domicilio: true,
      domicilio_edit_blocked_reason: null,
    });
    expect(fields.canEditDomicilio).toBe(true);
    expect(fields.domicilioEditBlockedReason).toBeNull();
  });

  it("reinspeccion por oficio bloquea domicilio y usa modo reinspeccion_oficio", () => {
    const fields = getActuacionEditableFields({
      ...baseRow,
      tipo_actuacion: "REINSPECCION",
      can_edit_domicilio: false,
      domicilio_edit_blocked_reason:
        "La actuaci?n proviene de una reinspecci?n y el domicilio no puede modificarse.",
      documentacion_contexto: { circuito: "REINSPECCION_OFICIO", propia: {} },
    });
    expect(fields.modoEdicion).toBe("reinspeccion_oficio");
    expect(fields.canEditContribuyente).toBe(false);
    expect(fields.canEditNotificacion).toBe(false);
    expect(fields.canEditActas).toBe(false);
    expect(fields.canEditDomicilio).toBe(false);
    expect(fields.domicilioEditBlockedReason).toBeTruthy();
  });

  it("ratificacion de clausura no permite editar contribuyente ni domicilio", () => {
    const fields = getActuacionEditableFields({
      ...baseRow,
      tipo_actuacion: "RATIFICACION DE CLAUSURA",
    });
    expect(fields.modoEdicion).toBe("ratificacion");
    expect(fields.canEditContribuyente).toBe(false);
    expect(fields.canEditDomicilio).toBe(false);
  });

  it("ratificaci?n de decomiso no permite editar contribuyente", () => {
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
    expect(fields.canEditActas).toBe(false);
  });

  it("verificar e informar con actas persistidas habilita bloque de actas", () => {
    const fields = getActuacionEditableFields({
      ...baseRow,
      tipo_actuacion: "VERIFICAR E INFORMAR",
      acta_inspeccion_num: "100/2026",
    });
    expect(fields.modoEdicion).toBe("verificar_informar");
    expect(fields.canEditActas).toBe(true);
  });
});

describe("resolveActuacionModoEdicion", () => {
  it("REINSPECCION + circuito OFICIO resuelve reinspeccion_oficio y no normal", () => {
    const row = {
      ...baseRow,
      tipo_actuacion: "REINSPECCION",
      documentacion_contexto: { circuito: "REINSPECCION_OFICIO", propia: {} },
    } as IActuacionListItem;
    expect(resolveActuacionModoEdicion(row)).toBe("reinspeccion_oficio");
    expect(resolveActuacionModoEdicion(row)).not.toBe("normal");
  });

  it("ratificaci?n clausura con circuito oficio sigue en modo ratificacion", () => {
    expect(
      resolveActuacionModoEdicion({
        ...baseRow,
        tipo_actuacion: "RATIFICACION DE CLAUSURA",
        documentacion_contexto: { circuito: "REINSPECCION_OFICIO", propia: {} },
      })
    ).toBe("ratificacion");
  });

  it("ratificaci?n decomiso con circuito oficio sigue en modo ratificacion", () => {
    expect(
      resolveActuacionModoEdicion({
        ...baseRow,
        tipo_actuacion: "RATIFICACION DE DECOMISO",
        documentacion_contexto: { circuito: "REINSPECCION_OFICIO", propia: {} },
      })
    ).toBe("ratificacion");
  });

  it("verificar e informar con circuito oficio sigue en modo verificar_informar", () => {
    expect(
      resolveActuacionModoEdicion({
        ...baseRow,
        tipo_actuacion: "VERIFICAR E INFORMAR",
        documentacion_contexto: { circuito: "REINSPECCION_OFICIO", propia: {} },
      })
    ).toBe("verificar_informar");
  });

  it("reinspecci?n por notificaci?n no regresa a normal", () => {
    expect(
      resolveActuacionModoEdicion({
        ...baseRow,
        tipo_actuacion: "REINSPECCION",
        documentacion_contexto: { circuito: "REINSPECCION_NOTIFICACION", propia: {} },
      })
    ).toBe("reinspeccion_notificacion");
  });

  it("F5: resuelve solo desde datos del row sin estado previo", () => {
    const rowSimulandoF5 = {
      id: 99,
      tipo_actuacion: "REINSPECCION",
      documentacion_contexto: { circuito: "REINSPECCION_OFICIO", propia: { oficio: "12/2026" } },
    } as IActuacionListItem;
    expect(resolveActuacionModoEdicion(rowSimulandoF5)).toBe("reinspeccion_oficio");
  });
});

describe("detectBlockedActaClearAttempt", () => {
  it("detecta borrado de acta de notificaci?n bloqueada", () => {
    const baseline = {
      ...baseRow,
      notificacion_editable: false,
      acta_notificacion_num: "100",
    } as IActuacionListItem;
    const draft = { ...baseline, acta_notificacion_num: "" };
    expect(detectBlockedActaClearAttempt(draft, baseline)).toBe(MENSAJE_BLOQUEO_ACTA_DOCUMENTACION);
  });

  it("detecta borrado de acta de comprobaci?n bloqueada", () => {
    const baseline = {
      ...baseRow,
      comprobacion_editable: false,
      acta_comprobacion_num: "200",
    } as IActuacionListItem;
    const draft = { ...baseline, acta_comprobacion_num: null };
    expect(detectBlockedActaClearAttempt(draft, baseline)).toBe(MENSAJE_BLOQUEO_ACTA_DOCUMENTACION);
  });
});

