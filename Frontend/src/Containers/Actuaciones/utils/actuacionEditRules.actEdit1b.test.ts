import { describe, expect, it } from "vitest";

import type { IActuacionListItem } from "../../../api/actuacionesListApi";
import {
  MENSAJE_BLOQUEO_REINSPECCION_DOMICILIO,
  esReinspeccionReal,
  getActuacionEditableFields,
  resolveActuacionModoEdicion,
} from "./actuacionEditRules";

const MSG_REINSPECCION = MENSAJE_BLOQUEO_REINSPECCION_DOMICILIO;

const inspeccionRelevamiento = (
  overrides: Partial<IActuacionListItem> = {}
): IActuacionListItem =>
  ({
    id: 4764,
    orden_trabajo_numero: "004764",
    tipo_actuacion: "INSPECCION",
    ruta_item_id: 120,
    can_edit_domicilio: false,
    can_edit_rubro: true,
    domicilio_edit_blocked_reason: MSG_REINSPECCION,
    documentacion_contexto: { circuito: "DESCONOCIDO", propia: {} },
    calle: "San Martín",
    numero: "100",
    rubro_nombre: "Bar",
    ...overrides,
  }) as IActuacionListItem;

describe("HOTFIX V1.1-ACT-EDIT.1B esReinspeccionReal", () => {
  it("Inspección desde Relevamiento no es reinspección real", () => {
    const row = inspeccionRelevamiento();
    expect(esReinspeccionReal(row)).toBe(false);
    expect(resolveActuacionModoEdicion(row)).toBe("normal");
    const fields = getActuacionEditableFields(row);
    expect(fields.canEditDomicilio).toBe(true);
    expect(fields.canEditRubro).toBe(true);
    expect(fields.domicilioEditBlockedReason).toBeNull();
  });

  it("Inspección de Relevamiento con Notificación y Comprobación sigue con domicilio editable", () => {
    const row = inspeccionRelevamiento({
      documentacion_contexto: { circuito: "COMUN_COMPROBACION", propia: {} },
      acta_inspeccion_num: "10",
      acta_notificacion_num: "20",
      notificacion_motivo_1: "Falta de habilitación",
      acta_comprobacion_num: "30",
      comprobacion_motivo: "Incumplimiento",
    });
    expect(esReinspeccionReal(row)).toBe(false);
    const fields = getActuacionEditableFields(row);
    expect(fields.canEditDomicilio).toBe(true);
    expect(fields.domicilioEditBlockedReason).toBeNull();
  });

  it("actuación manual sin RutaItem no es reinspección real", () => {
    const row = inspeccionRelevamiento({
      ruta_item_id: null,
      documentacion_contexto: { circuito: "COMUN_NOTIFICACION", propia: {} },
    });
    expect(esReinspeccionReal(row)).toBe(false);
    expect(getActuacionEditableFields(row).canEditDomicilio).toBe(true);
  });

  it("reinspección real por notificación bloquea domicilio y muestra el mensaje", () => {
    const row = inspeccionRelevamiento({
      tipo_actuacion: "REINSPECCION",
      can_edit_rubro: false,
      documentacion_contexto: { circuito: "REINSPECCION_NOTIFICACION", propia: {} },
      origen_reinspeccion_notificacion: {
        notificacion_acta_numero: "20",
        notificacion_acta_anio: 2026,
      },
    });
    expect(esReinspeccionReal(row)).toBe(true);
    const fields = getActuacionEditableFields(row);
    expect(fields.modoEdicion).toBe("reinspeccion_notificacion");
    expect(fields.canEditDomicilio).toBe(false);
    expect(fields.domicilioEditBlockedReason).toBe(MSG_REINSPECCION);
  });

  it("reinspección real por oficio bloquea domicilio", () => {
    const row = inspeccionRelevamiento({
      tipo_actuacion: "REINSPECCION",
      can_edit_rubro: false,
      documentacion_contexto: { circuito: "REINSPECCION_OFICIO", propia: {} },
      origen_reinspeccion_oficio: {
        oficio_numero: "12",
        oficio_anio: 2026,
      },
    });
    expect(esReinspeccionReal(row)).toBe(true);
    const fields = getActuacionEditableFields(row);
    expect(fields.canEditDomicilio).toBe(false);
    expect(fields.domicilioEditBlockedReason).toBe(MSG_REINSPECCION);
  });
});
