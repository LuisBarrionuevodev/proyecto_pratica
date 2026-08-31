import { describe, expect, it } from "vitest";

import type { IActuacionListItem } from "../../../api/actuacionesListApi";
import {
  debeMostrarActaPersistidaParaQuitar,
  debeMostrarCampoActaEnEdicion,
  getActuacionEditableFields,
} from "./actuacionEditRules";

const verificarRow = (overrides: Partial<IActuacionListItem> = {}): IActuacionListItem =>
  ({
    id: 1,
    tipo_actuacion: "VERIFICAR E INFORMAR",
    realizo_nueva_inspeccion: true,
    documentacion_contexto: { circuito: "REINSPECCION_OFICIO", propia: {} },
    acta_inspeccion_num: "005032",
    acta_notificacion_num: "001234",
    notificacion_motivo_1: "Falta de habilitación",
    acta_comprobacion_num: null,
    acta_clausura_num: null,
    acta_decomiso_num: null,
    ...overrides,
  }) as IActuacionListItem;

describe("GESTIÓN-FIX.6 actuacionEditRules", () => {
  it("denuncia: canEditRubro true con can_edit_rubro backend", () => {
    const row = {
      id: 1,
      tipo_actuacion: "INSPECCION",
      can_edit_domicilio: false,
      can_edit_rubro: true,
    } as IActuacionListItem;
    const fields = getActuacionEditableFields(row);
    expect(fields.canEditDomicilio).toBe(false);
    expect(fields.canEditRubro).toBe(true);
  });

  it("debeMostrarActaPersistidaParaQuitar detecta notificación persistida", () => {
    const row = verificarRow();
    expect(debeMostrarActaPersistidaParaQuitar("NOTIFICACION", row)).toBe(true);
    expect(debeMostrarActaPersistidaParaQuitar("INSPECCION", row)).toBe(true);
  });

  it("verificar CONTRA: notificación visible para quitar sin validar inspección", () => {
    const baseline = verificarRow();
    const fields = getActuacionEditableFields(baseline, {
      oficioSubtipo: "VERIFICAR E INFORMAR",
      verificarEstadoOperativo: "CONTRAPRODUCENCIA",
      baselineRow: baseline,
    });
    expect(fields.debeValidarActasInspeccionNormal).toBe(false);
    expect(fields.canEditNotificacion).toBe(false);
    expect(debeMostrarCampoActaEnEdicion("NOTIFICACION", baseline, fields, baseline)).toBe(
      true
    );
    expect(debeMostrarCampoActaEnEdicion("INSPECCION", baseline, fields, baseline)).toBe(true);
    expect(debeMostrarCampoActaEnEdicion("COMPROBACION", baseline, fields, baseline)).toBe(
      false
    );
  });

  it("verificar SI_INSPECCION: muestra todos los inputs de actas soportados", () => {
    const row = verificarRow({
      acta_inspeccion_num: null,
      acta_notificacion_num: null,
      notificacion_motivo_1: null,
    });
    const fields = getActuacionEditableFields(row, {
      oficioSubtipo: "VERIFICAR E INFORMAR",
      verificarEstadoOperativo: "SI_INSPECCION",
    });
    expect(fields.debeValidarActasInspeccionNormal).toBe(true);
    expect(fields.canEditNotificacion).toBe(true);
    for (const tipo of [
      "INSPECCION",
      "NOTIFICACION",
      "COMPROBACION",
      "CLAUSURA",
      "DECOMISO",
    ] as const) {
      expect(debeMostrarCampoActaEnEdicion(tipo, row, fields)).toBe(true);
    }
  });

  it("ratificación→verificar SI: actas completas sin domicilio editable", () => {
    const row = {
      id: 1,
      tipo_actuacion: "VERIFICAR E INFORMAR",
      realizo_nueva_inspeccion: true,
      documentacion_contexto: { circuito: "REINSPECCION_OFICIO", propia: {} },
      can_edit_domicilio: false,
      can_edit_rubro: false,
    } as IActuacionListItem;
    const fields = getActuacionEditableFields(row, {
      oficioSubtipo: "VERIFICAR E INFORMAR",
      verificarEstadoOperativo: "SI_INSPECCION",
    });
    expect(fields.canEditDomicilio).toBe(false);
    expect(fields.canEditRubro).toBe(false);
    expect(fields.canEditContribuyente).toBe(false);
    expect(debeMostrarCampoActaEnEdicion("NOTIFICACION", row, fields)).toBe(true);
  });

  it("canEditActas permanece con baseline aunque draft vacíe inspección", () => {
    const baseline = verificarRow();
    const draft = { ...baseline, acta_inspeccion_num: null };
    const fields = getActuacionEditableFields(draft, {
      oficioSubtipo: "VERIFICAR E INFORMAR",
      verificarEstadoOperativo: "CONTRAPRODUCENCIA",
      baselineRow: baseline,
    });
    expect(fields.canEditActas).toBe(true);
  });
});
