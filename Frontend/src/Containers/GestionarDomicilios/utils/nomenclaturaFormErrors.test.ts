import { describe, expect, it } from "vitest";

import {
  applyNomenclaturaErrorsFromApi,
  mapClientNomenclaturaError,
} from "./nomenclaturaFormErrors";

describe("nomenclaturaFormErrors", () => {
  it("mapea detail pydantic array a campo numero", () => {
    const err = {
      response: {
        status: 422,
        data: { detail: [{ loc: ["numero"], msg: "Campo obligatorio" }] },
      },
    };
    const { fieldErrors } = applyNomenclaturaErrorsFromApi(err);
    expect(fieldErrors.numero).toBe("Campo obligatorio");
  });

  it("mapea error local de calle a calle_input", () => {
    const { fieldErrors } = mapClientNomenclaturaError(
      'Modo calle "Catálogo": seleccione una calle del catálogo.'
    );
    expect(fieldErrors.calle_input).toContain("calle");
  });

  it("error global sin campo usa globalMessage", () => {
    const { fieldErrors, globalMessage } = applyNomenclaturaErrorsFromApi({
      response: { status: 500, data: { detail: "Error interno" } },
    });
    expect(Object.keys(fieldErrors)).toHaveLength(0);
    expect(globalMessage).toBe("Error interno");
  });
});
