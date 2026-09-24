import { describe, expect, it } from "vitest";

import type { IActuacionListItem } from "../../../api/actuacionesListApi";
import {
  actuacionBloqueadaPorExpedienteTotal,
  resolveActuacionEditStart,
} from "./actuacionEditRules";
import {
  buildInspectoresForCanal,
  inspectoresListEqual,
} from "./buildInspectoresForCanal";

const baseRow = { id: 1 } as IActuacionListItem;

describe("GESTIÓN-FIX.10A — expediente RN", () => {
  it("B1: RN con notificación origen readonly permite Editar", () => {
    const result = resolveActuacionEditStart({
      ...baseRow,
      notificacion_editable: false,
      actuacion_bloqueada_por_expediente: false,
    });
    expect(result).toEqual({ allowed: true });
  });

  it("B2: comprobación readonly no bloquea modal", () => {
    const result = resolveActuacionEditStart({
      ...baseRow,
      comprobacion_editable: false,
    });
    expect(result).toEqual({ allowed: true });
  });

  it("B3: actuacion_editable false sigue bloqueando", () => {
    const result = resolveActuacionEditStart({
      ...baseRow,
      actuacion_editable: false,
    });
    expect(result.allowed).toBe(false);
  });

  it("bloqueo total solo con actuacion_bloqueada_por_expediente", () => {
    expect(actuacionBloqueadaPorExpedienteTotal({ ...baseRow, comprobacion_editable: false })).toBe(
      false
    );
    expect(
      actuacionBloqueadaPorExpedienteTotal({ ...baseRow, actuacion_bloqueada_por_expediente: true })
    ).toBe(true);
  });
});

describe("GESTIÓN-FIX.10A — inspectores", () => {
  it("buildInspectoresForCanal usa slots si inspectores=[]", () => {
    const row = {
      ...baseRow,
      inspectores: [],
      inspector1: "Accardi",
      inspector2: "Alamo",
    } as IActuacionListItem;
    expect(buildInspectoresForCanal(row)).toEqual(["Accardi", "Alamo"]);
  });

  it("buildInspectoresForCanal prioriza lista no vacía", () => {
    const row = {
      ...baseRow,
      inspectores: ["García"],
      inspector1: "Accardi",
    } as IActuacionListItem;
    expect(buildInspectoresForCanal(row)).toEqual(["García"]);
  });

  it("inspectoresListEqual compara orden", () => {
    expect(inspectoresListEqual(["A", "B"], ["A", "B"])).toBe(true);
    expect(inspectoresListEqual(["A", "B"], ["B", "A"])).toBe(false);
  });
});
