import { describe, expect, it } from "vitest";

import type { IActuacionListItem } from "../../api/actuacionesListApi";
import {
  omiteIdentidadOperativaRow,
  resolveCircuitoOperativo,
} from "./resolveCircuitoOperativo";
import { actuacionCrudValidationContext, validateActuacionFormForSubmit } from "../../Containers/Actuaciones/validations/actuacionFormValidation";

const rnRow = (overrides: Partial<IActuacionListItem> = {}): IActuacionListItem =>
  ({
    id: 1,
    tipo_actuacion: "REINSPECCION",
    documentacion_contexto: { circuito: "REINSPECCION_NOTIFICACION", propia: {} },
    can_edit_domicilio: true,
    calle: "",
    rubro_nombre: "",
    fecha_actuacion: "2026-01-15",
    inspector1: "A",
    inspector2: "B",
    ...overrides,
  }) as IActuacionListItem;

describe("resolveCircuitoOperativo FIX.9", () => {
  it("detecta RN por circuito documental", () => {
    expect(resolveCircuitoOperativo(rnRow())).toBe("REINSPECCION_NOTIFICACION");
    expect(omiteIdentidadOperativaRow(rnRow())).toBe(true);
  });

  it("RN no exige calle aunque can_edit_domicilio sea true", () => {
    const row = rnRow({ can_edit_domicilio: true, calle: "", rubro_nombre: "" });
    const ctx = actuacionCrudValidationContext(row);
    expect(ctx.omiteIdentidadOperativa).toBe(true);
    const result = validateActuacionFormForSubmit(row, ctx);
    expect(result.fieldErrors.calle).toBeUndefined();
    expect(result.fieldErrors.rubro_nombre).toBeUndefined();
  });
});
