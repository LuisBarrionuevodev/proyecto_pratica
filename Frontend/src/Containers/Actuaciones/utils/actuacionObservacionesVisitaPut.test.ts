import { describe, expect, it } from "vitest";
import type { IActuacionListItem } from "../../../api/actuacionesListApi";
import {
  buildObservacionesEjecucionPutFields,
  canEditObservacionesVisita,
  observacionesVisitaDisplayText,
  validateObservacionesVisitaFields,
} from "./actuacionObservacionesVisitaPut";

const base: IActuacionListItem = {
  id: 1,
  ruta_item_id: 10,
  actuacion_editable: true,
  observaciones_ejecucion: "Visita OK",
} as IActuacionListItem;

describe("actuacionObservacionesVisitaPut", () => {
  it("muestra guión si no hay texto", () => {
    expect(observacionesVisitaDisplayText({ ...base, observaciones_ejecucion: null })).toBe("—");
    expect(observacionesVisitaDisplayText({ ...base, observaciones_ejecucion: "  " })).toBe("—");
  });

  it("canEditObservacionesVisita exige ruta_item y actuacion_editable", () => {
    expect(canEditObservacionesVisita(base)).toBe(true);
    expect(canEditObservacionesVisita({ ...base, ruta_item_id: null })).toBe(false);
    expect(canEditObservacionesVisita({ ...base, actuacion_editable: false })).toBe(false);
  });

  it("buildObservacionesEjecucionPutFields recorta y normaliza vacío a null", () => {
    expect(buildObservacionesEjecucionPutFields(base)).toEqual({
      observaciones_ejecucion: "Visita OK",
    });
    expect(
      buildObservacionesEjecucionPutFields({ ...base, observaciones_ejecucion: "  x  " })
    ).toEqual({ observaciones_ejecucion: "x" });
    expect(
      buildObservacionesEjecucionPutFields({ ...base, observaciones_ejecucion: "   " })
    ).toEqual({ observaciones_ejecucion: null });
    expect(buildObservacionesEjecucionPutFields({ ...base, ruta_item_id: null })).toEqual({});
  });

  it("validateObservacionesVisitaFields limita longitud", () => {
    expect(validateObservacionesVisitaFields(base)).toEqual({});
    const long = "a".repeat(4001);
    expect(validateObservacionesVisitaFields({ ...base, observaciones_ejecucion: long })).toEqual({
      observaciones_ejecucion: "Máximo 4000 caracteres.",
    });
  });
});
