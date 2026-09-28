import { describe, expect, it } from "vitest";

import type { IRelevamiento } from "../types/relevamientos";
import { validateRelevamiento } from "./validations";

function baseRelevamiento(overrides: Partial<IRelevamiento> = {}): IRelevamiento {
  return {
    id: 1,
    fecha: null,
    relevadores_label: "Relevador Test",
    calle: "Maipú",
    numero: "100",
    rubro: "Panadería",
    ...overrides,
  };
}

describe("validateRelevamiento — fecha opcional", () => {
  it("fecha undefined → sin errors.fecha", () => {
    const { fecha: _omit, ...rest } = baseRelevamiento();
    const errors = validateRelevamiento(rest as IRelevamiento);
    expect(errors.fecha).toBeUndefined();
  });

  it("fecha null/vacía → sin errors.fecha", () => {
    expect(validateRelevamiento(baseRelevamiento({ fecha: null })).fecha).toBeUndefined();
    expect(validateRelevamiento(baseRelevamiento({ fecha: "" })).fecha).toBeUndefined();
    expect(validateRelevamiento(baseRelevamiento({ fecha: "   " })).fecha).toBeUndefined();
  });

  it("fecha válida → sin error", () => {
    const errors = validateRelevamiento(baseRelevamiento({ fecha: "2026-05-10" }));
    expect(errors.fecha).toBeUndefined();
  });

  it("fecha mal formada → error", () => {
    const errors = validateRelevamiento(baseRelevamiento({ fecha: "10/05/2026" }));
    expect(errors.fecha).toMatch(/Formato de fecha incorrecto/);
  });

  it("fecha imposible → error", () => {
    const errors = validateRelevamiento(baseRelevamiento({ fecha: "2026-02-30" }));
    expect(errors.fecha).toBe("Fecha inválida");
  });
});
