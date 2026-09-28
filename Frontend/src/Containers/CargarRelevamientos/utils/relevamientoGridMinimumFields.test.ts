import { describe, expect, it } from "vitest";

import type { GridRow } from "../../../api/gridApi";
import {
  RELEVAMIENTO_MIN_VISUAL_FIELD_IDS,
  relevamientoRowMinimumCompleteForVisual,
} from "./relevamientoGridMinimumFields";

describe("relevamientoGridMinimumFields", () => {
  it("no incluye Fecha en el mínimo visual", () => {
    expect(RELEVAMIENTO_MIN_VISUAL_FIELD_IDS).not.toContain("Fecha");
    expect(RELEVAMIENTO_MIN_VISUAL_FIELD_IDS).toEqual([
      "Relevador",
      "Calle",
      "Numero",
      "Rubro",
    ]);
  });

  it("fila con relevador, calle, número y rubro sin fecha cumple mínimo visual", () => {
    const row = {
      Relevador: "Fabian Esquivel",
      Calle: "Maipú",
      Numero: "100",
      Rubro: "Panadería",
    } as GridRow;
    expect(relevamientoRowMinimumCompleteForVisual(row)).toBe(true);
  });

  it("fila incompleta no cumple mínimo visual", () => {
    const row = {
      Relevador: "Fabian Esquivel",
      Calle: "Maipú",
      Numero: "",
      Rubro: "Panadería",
    } as GridRow;
    expect(relevamientoRowMinimumCompleteForVisual(row)).toBe(false);
  });
});
