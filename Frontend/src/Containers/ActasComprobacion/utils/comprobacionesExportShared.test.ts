import { describe, expect, it } from "vitest";

import { domicilioFromParts } from "./comprobacionesExportShared";

describe("comprobacionesExportShared domicilio PR10.4b.6", () => {
  it("muestra domicilio normalizado si calle_estado OK", () => {
    expect(
      domicilioFromParts("raw", "1", {
        calle_estado: "OK",
        calle_normalizada: "San Martín",
        calle: "raw relevamiento",
        numero: "2869",
      })
    ).toBe("San Martín 2869");
  });

  it("fallback raw si no hay normalizado", () => {
    expect(domicilioFromParts("Calle Vieja", "50")).toBe("Calle Vieja 50");
  });
});
