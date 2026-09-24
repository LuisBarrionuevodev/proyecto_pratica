import { describe, expect, it } from "vitest";

import {
  EXPEDIENTE_ACTUALIZADO_MSG,
  EXPEDIENTE_ELIMINADO_MSG,
  prorrogaAltaSuccessMessage,
} from "./prorrogaSuccessMessage";

describe("prorrogaSuccessMessage", () => {
  it("alta sin volver en plazo", () => {
    expect(prorrogaAltaSuccessMessage(false)).toBe("Expediente registrado correctamente.");
  });

  it("alta volviendo en plazo", () => {
    expect(prorrogaAltaSuccessMessage(true)).toContain("Expediente registrado correctamente.");
    expect(prorrogaAltaSuccessMessage(true)).toContain("en plazo");
  });

  it("mensajes patch y delete", () => {
    expect(EXPEDIENTE_ACTUALIZADO_MSG).toBe("Expediente actualizado correctamente.");
    expect(EXPEDIENTE_ELIMINADO_MSG).toBe("Expediente eliminado correctamente.");
  });
});
