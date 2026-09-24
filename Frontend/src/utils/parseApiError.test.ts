import { describe, expect, it } from "vitest";

import {
  DEFAULT_FIELD_ERROR_SUMMARY,
  applyFormErrorsFromMap,
  mapApiErrorsToFormState,
  mapBusinessDetailToFieldErrors,
  parseApiError,
} from "./parseApiError";

describe("parseApiError", () => {
  it("mapea errors por campo a fieldErrors", () => {
    const err = {
      response: {
        data: {
          errors: { contraproducencia: "Elegí una contraproducencia." },
        },
      },
    };
    const parsed = mapApiErrorsToFormState(err);
    expect(parsed.fieldErrors.contraproducencia).toBe("Elegí una contraproducencia.");
    expect(parsed.globalMessage).toBe(DEFAULT_FIELD_ERROR_SUMMARY);
  });

  it("no duplica mensaje de campo en global cuando hay inline", () => {
    const result = applyFormErrorsFromMap({
      numero_oficio: "Ya existe",
      _row: "Revisá el formulario",
    });
    expect(result.fieldErrors.numero_oficio).toBe("Ya existe");
    expect(result.globalMessage).toContain(DEFAULT_FIELD_ERROR_SUMMARY);
    expect(result.globalMessage).not.toContain("Ya existe");
  });

  it("acepta errors como array pydantic", () => {
    const err = {
      response: {
        data: {
          errors: [{ loc: ["numero_oficio"], msg: "Campo obligatorio" }],
        },
      },
    };
    const parsed = parseApiError(err);
    expect(parsed.rawFieldErrors?.numero_oficio).toBe("Campo obligatorio");
  });

  it("mapea detail de negocio a campo cuando no hay errors", () => {
    const fields = mapBusinessDetailToFieldErrors("El numero_oficio ya existe para el año");
    expect(fields?.numero_oficio).toContain("numero_oficio");
  });

  it("global único cuando no hay field errors", () => {
    const parsed = mapApiErrorsToFormState({
      response: { data: { detail: "Permiso denegado" } },
    });
    expect(Object.keys(parsed.fieldErrors)).toHaveLength(0);
    expect(parsed.globalMessage).toBe("Permiso denegado");
  });
});
