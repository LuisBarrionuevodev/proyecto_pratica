import { describe, expect, it } from "vitest";

import type { IActuacionListItem } from "../../../api/actuacionesListApi";
import {
  MENSAJE_BLOQUEO_REINSPECCION_DOMICILIO,
  esReinspeccionReal,
  getActuacionEditableFields,
  resolveActuacionModoEdicion,
} from "./actuacionEditRules";

const MSG_REINSPECCION = MENSAJE_BLOQUEO_REINSPECCION_DOMICILIO;
const MSG_ACTAS_DOCUMENTALES =
  "El domicilio no puede modificarse porque el acta ya fue utilizada en un circuito posterior.";

const inspeccionNormal = (overrides: Partial<IActuacionListItem> = {}): IActuacionListItem =>
  ({
    id: 91,
    tipo_actuacion: "INSPECCION",
    can_edit_domicilio: false,
    can_edit_rubro: true,
    documentacion_contexto: { circuito: "DESCONOCIDO", propia: {} },
    calle: "San Martín",
    numero: "100",
    numero_tipo: "NUMERO",
    contribuyente: { apellido: "Pérez", nombre: "Juan" },
    ...overrides,
  }) as IActuacionListItem;

describe("HOTFIX V1.1-ACT-EDIT.1C domicilio en inspecciones normales", () => {
  it("Relevamiento: domicilio editable sin mensaje de reinspección", () => {
    const row = inspeccionNormal({
      ruta_item_id: 120,
      domicilio_edit_blocked_reason: MSG_REINSPECCION,
    });
    expect(esReinspeccionReal(row)).toBe(false);
    expect(resolveActuacionModoEdicion(row)).toBe("normal");
    const fields = getActuacionEditableFields(row);
    expect(fields.canEditDomicilio).toBe(true);
    expect(fields.domicilioEditBlockedReason).toBeNull();
  });

  it("Denuncia: domicilio editable aunque GET marque can_edit_domicilio false", () => {
    const row = inspeccionNormal({
      ruta_item_id: 88,
      can_edit_domicilio: false,
      can_edit_rubro: true,
    });
    expect(esReinspeccionReal(row)).toBe(false);
    const fields = getActuacionEditableFields(row);
    expect(fields.canEditDomicilio).toBe(true);
    expect(fields.canEditRubro).toBe(true);
    expect(fields.domicilioEditBlockedReason).toBeNull();
  });

  it("Carga manual: domicilio editable", () => {
    const row = inspeccionNormal({
      ruta_item_id: null,
      can_edit_domicilio: true,
    });
    expect(getActuacionEditableFields(row).canEditDomicilio).toBe(true);
  });

  it("reinspección real por notificación sigue bloqueada", () => {
    const row = inspeccionNormal({
      tipo_actuacion: "REINSPECCION",
      can_edit_rubro: false,
      documentacion_contexto: { circuito: "REINSPECCION_NOTIFICACION", propia: {} },
      origen_reinspeccion_notificacion: {
        notificacion_acta_numero: "20",
        notificacion_acta_anio: 2026,
      },
      domicilio_edit_blocked_reason: MSG_REINSPECCION,
    });
    expect(esReinspeccionReal(row)).toBe(true);
    const fields = getActuacionEditableFields(row);
    expect(fields.canEditDomicilio).toBe(false);
    expect(fields.domicilioEditBlockedReason).toBe(MSG_REINSPECCION);
  });

  it("circuito posterior sigue bloqueando domicilio", () => {
    const row = inspeccionNormal({
      can_edit_rubro: false,
      domicilio_edit_blocked_reason: MSG_ACTAS_DOCUMENTALES,
      documentacion_contexto: { circuito: "COMUN_NOTIFICACION", propia: {} },
    });
    const fields = getActuacionEditableFields(row);
    expect(fields.canEditDomicilio).toBe(false);
    expect(fields.domicilioEditBlockedReason).toContain("circuito posterior");
  });
});
