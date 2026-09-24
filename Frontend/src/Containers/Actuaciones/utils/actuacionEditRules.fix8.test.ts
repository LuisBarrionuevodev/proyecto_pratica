import { describe, expect, it } from "vitest";

import type { IActuacionListItem } from "../../../api/actuacionesListApi";
import {
  debeMostrarCampoActaEnEdicion,
  getActuacionEditableFields,
} from "./actuacionEditRules";

const rnRow = (overrides: Partial<IActuacionListItem> = {}): IActuacionListItem =>
  ({
    id: 1,
    tipo_actuacion: "REINSPECCION",
    documentacion_contexto: { circuito: "REINSPECCION_NOTIFICACION", propia: {} },
    origen_reinspeccion_notificacion: { notificacion_acta_numero: "001234" },
    acta_inspeccion_num: "005032",
    acta_notificacion_num: null,
    acta_comprobacion_num: null,
    acta_clausura_num: null,
    acta_decomiso_num: null,
    ...overrides,
  }) as IActuacionListItem;

describe("GESTIÓN-FIX.8 / FIX.9 actuacionEditRules", () => {
  it("N10: reinspección notificación realizada muestra actas de visita editables", () => {
    const row = rnRow();
    const fields = getActuacionEditableFields(row);
    expect(fields.modoEdicion).toBe("reinspeccion_notificacion");
    expect(fields.canEditNotificacion).toBe(false);
    expect(debeMostrarCampoActaEnEdicion("NOTIFICACION", row, fields)).toBe(false);
    expect(debeMostrarCampoActaEnEdicion("INSPECCION", row, fields)).toBe(true);
    expect(debeMostrarCampoActaEnEdicion("COMPROBACION", row, fields)).toBe(true);
    expect(debeMostrarCampoActaEnEdicion("CLAUSURA", row, fields)).toBe(true);
    expect(debeMostrarCampoActaEnEdicion("DECOMISO", row, fields)).toBe(true);
  });

  it("FIX.9: RN con contraproducencia solo muestra actas persistidas", () => {
    const row = rnRow({
      contraproducencia: "LOCAL CERRADO",
      acta_inspeccion_num: "005032",
      acta_comprobacion_num: null,
    });
    const fields = getActuacionEditableFields(row);
    expect(debeMostrarCampoActaEnEdicion("INSPECCION", row, fields)).toBe(true);
    expect(debeMostrarCampoActaEnEdicion("COMPROBACION", row, fields)).toBe(false);
    expect(debeMostrarCampoActaEnEdicion("CLAUSURA", row, fields)).toBe(false);
  });
});
