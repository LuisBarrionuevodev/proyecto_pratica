import { describe, expect, it } from "vitest";

import type { IActuacionListItem } from "../../../api/actuacionesListApi";
import {
  actaComprobacionBloqueadaEdicion,
  actaNotificacionBloqueadaEdicion,
  esBloqueoFalsoReinspeccionEnActuacionBase,
  getActuacionEditableFields,
  resolveActuacionModoEdicion,
} from "./actuacionEditRules";

const MSG_REINSPECCION =
  "La actuación proviene de una reinspección y el domicilio no puede modificarse.";
const MSG_ACTAS_DOCUMENTALES =
  "El domicilio no puede modificarse porque el acta ya fue utilizada en un circuito posterior.";

const baseInspeccion = (overrides: Partial<IActuacionListItem> = {}): IActuacionListItem =>
  ({
    id: 42,
    tipo_actuacion: "INSPECCION",
    acta_inspeccion_num: "100",
    acta_notificacion_num: "200",
    notificacion_motivo_1: "Falta de habilitación",
    ...overrides,
  }) as IActuacionListItem;

describe("V1.1-ACT-EDIT.1 actuación base vs reinspección", () => {
  it("actuación base con iniciador RN derivado no entra en modo reinspección", () => {
    const row = baseInspeccion({
      can_edit_domicilio: false,
      can_edit_rubro: false,
      domicilio_edit_blocked_reason: MSG_REINSPECCION,
      documentacion_contexto: { circuito: "COMUN_NOTIFICACION", propia: {} },
    });
    expect(resolveActuacionModoEdicion(row)).toBe("normal");
    expect(esBloqueoFalsoReinspeccionEnActuacionBase(row, "normal")).toBe(true);
    const fields = getActuacionEditableFields(row);
    expect(fields.modoEdicion).toBe("normal");
    expect(fields.canEditDomicilio).toBe(true);
    expect(fields.canEditRubro).toBe(true);
    expect(fields.domicilioEditBlockedReason).toBeNull();
    expect(fields.canEditContribuyente).toBe(true);
  });

  it("tipo REINSPECCION sin circuito documental sigue bloqueando domicilio", () => {
    const row = baseInspeccion({
      tipo_actuacion: "REINSPECCION",
      can_edit_domicilio: false,
      can_edit_rubro: false,
      domicilio_edit_blocked_reason: MSG_REINSPECCION,
    });
    const fields = getActuacionEditableFields(row);
    expect(fields.canEditDomicilio).toBe(false);
    expect(fields.canEditRubro).toBe(false);
  });

  it("reinspección real conserva bloqueo de calle, número y rubro", () => {
    const row = baseInspeccion({
      tipo_actuacion: "REINSPECCION",
      can_edit_domicilio: false,
      can_edit_rubro: false,
      domicilio_edit_blocked_reason: MSG_REINSPECCION,
      documentacion_contexto: { circuito: "REINSPECCION_NOTIFICACION", propia: {} },
      origen_reinspeccion_notificacion: {
        notificacion_acta_numero: "200",
        notificacion_acta_anio: 2026,
      },
      ruta_item_id: 88,
    });
    expect(resolveActuacionModoEdicion(row)).toBe("reinspeccion_notificacion");
    const fields = getActuacionEditableFields(row);
    expect(fields.canEditDomicilio).toBe(false);
    expect(fields.canEditRubro).toBe(false);
    expect(fields.canEditContribuyente).toBe(false);
    expect(fields.domicilioEditBlockedReason).toContain("reinspección");
  });

  it("denuncia sigue con domicilio bloqueado y rubro editable", () => {
    const row = baseInspeccion({
      can_edit_domicilio: false,
      can_edit_rubro: true,
      domicilio_edit_blocked_reason: MSG_REINSPECCION,
    });
    const fields = getActuacionEditableFields(row);
    expect(fields.modoEdicion).toBe("normal");
    expect(fields.canEditDomicilio).toBe(false);
    expect(fields.canEditRubro).toBe(true);
  });

  it("acta usada en circuito posterior sigue bloqueando domicilio", () => {
    const row = baseInspeccion({
      can_edit_domicilio: false,
      can_edit_rubro: false,
      domicilio_edit_blocked_reason: MSG_ACTAS_DOCUMENTALES,
      documentacion_contexto: { circuito: "COMUN_NOTIFICACION", propia: {} },
    });
    const fields = getActuacionEditableFields(row);
    expect(fields.canEditDomicilio).toBe(false);
    expect(fields.canEditRubro).toBe(false);
    expect(fields.domicilioEditBlockedReason).toContain("circuito posterior");
  });

  it("acta de notificación con expediente y comprobación con oficio siguen bloqueadas", () => {
    const row = baseInspeccion({
      can_edit_domicilio: false,
      can_edit_rubro: false,
      domicilio_edit_blocked_reason: MSG_REINSPECCION,
      documentacion_contexto: { circuito: "COMUN_NOTIFICACION", propia: {} },
      notificacion_editable: false,
      comprobacion_editable: false,
      acta_comprobacion_num: "300",
    });
    const fields = getActuacionEditableFields(row);
    expect(fields.canEditDomicilio).toBe(true);
    expect(actaNotificacionBloqueadaEdicion(row)).toBe(true);
    expect(actaComprobacionBloqueadaEdicion(row)).toBe(true);
  });
});
