import { describe, expect, it } from "vitest";

import { establecimientoDomicilioLineaVisible } from "./establecimientoDomicilioVisible";

describe("establecimientoDomicilioVisible PR10.4b.5", () => {
  it("prioriza domicilio_texto del API", () => {
    expect(
      establecimientoDomicilioLineaVisible({
        domicilio_texto: "San Martín 2869",
        calle: "calle raw",
        calle_normalizada: null,
        numero: "1",
      })
    ).toBe("San Martín 2869");
  });

  it("fallback local usa calle normalizada sobre raw", () => {
    expect(
      establecimientoDomicilioLineaVisible({
        domicilio_texto: null,
        calle: "calle raw relevamiento",
        calle_normalizada: "San Martín",
        numero: "2869",
      })
    ).toBe("San Martín 2869");
  });

  it("sin datos muestra guión", () => {
    expect(
      establecimientoDomicilioLineaVisible({
        domicilio_texto: null,
        calle: null,
        calle_normalizada: null,
        numero: null,
      })
    ).toBe("—");
  });
});
