import { describe, expect, it } from "vitest";

import type { IActuacionListItem } from "../../../api/actuacionesListApi";
import { getActuacionEditableFields } from "./actuacionEditRules";

const oficioRow = (overrides: Partial<IActuacionListItem> = {}): IActuacionListItem =>
  ({
    id: 1,
    tipo_actuacion: "VERIFICAR E INFORMAR",
    realizo_nueva_inspeccion: true,
    documentacion_contexto: { circuito: "REINSPECCION_OFICIO", propia: {} },
    can_edit_domicilio: true,
    can_edit_rubro: true,
    can_edit_contribuyente: true,
    ...overrides,
  }) as IActuacionListItem;

describe("GESTIÓN-FIX.7 actuacionEditRules", () => {
  it("O1/O2: Oficio bloquea identidad aunque backend marque can_edit_domicilio=true", () => {
    const row = oficioRow({ can_edit_domicilio: true, can_edit_rubro: true });
    const fields = getActuacionEditableFields(row, {
      oficioSubtipo: "VERIFICAR E INFORMAR",
      verificarEstadoOperativo: "SI_INSPECCION",
    });
    expect(fields.canEditDomicilio).toBe(false);
    expect(fields.canEditRubro).toBe(false);
    expect(fields.canEditContribuyente).toBe(false);
    expect(fields.canEditNombreLocal).toBe(false);
    expect(fields.canEditActas).toBe(true);
  });
});
