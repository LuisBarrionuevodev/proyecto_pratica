import { describe, expect, it } from "vitest";

import { domicilioLineaOperativo } from "./formatDomicilioLineaVisible";

describe("domicilioLineaOperativo PR10.4b.6", () => {
  it("prioriza domicilio_texto del API", () => {
    expect(
      domicilioLineaOperativo({
        domicilio_texto: "San Martín 2869",
        calle: "raw",
        calle_normalizada: "Otra",
        numero: "1",
      })
    ).toBe("San Martín 2869");
  });

  it("usa calle normalizada cuando calle_estado es OK", () => {
    expect(
      domicilioLineaOperativo({
        calle_estado: "OK",
        calle_normalizada: "San Martín",
        calle: "calle raw",
        numero: "2869",
      })
    ).toBe("San Martín 2869");
  });

  it("fallback raw sin romper si no hay normalizado", () => {
    expect(
      domicilioLineaOperativo({
        calle: "Calle Sin Normalizar",
        numero: "100",
      })
    ).toBe("Calle Sin Normalizar 100");
  });
});
