import { describe, expect, it } from "vitest";

import { domicilioLinea } from "./notificacionesExportShared";

describe("notificacionesExportShared domicilio PR10.4b.6", () => {
  it("muestra domicilio normalizado si calle_estado OK", () => {
    expect(
      domicilioLinea({
        id: 1,
        calle_estado: "OK",
        calle_normalizada: "San Martín",
        calle: "raw relevamiento",
        numero: "2869",
      } as never)
    ).toBe("San Martín 2869");
  });

  it("fallback raw si no hay normalizado", () => {
    expect(
      domicilioLinea({
        id: 1,
        calle: "Calle Vieja",
        numero: "50",
      } as never)
    ).toBe("Calle Vieja 50");
  });
});
