import { describe, expect, it } from "vitest";

import {
  buildBloqueDireccionOperativaPdf,
  buildEstablecimientoSecundarioText,
} from "./establecimientoSecundario";

describe("establecimientoSecundario documentos utils", () => {
  it("solo nombre fantasía", () => {
    expect(buildEstablecimientoSecundarioText({ nombre_fantasia: "El Toro" })).toBe(
      "Nombre fantasía: El Toro"
    );
  });

  it("solo ángulo", () => {
    expect(buildEstablecimientoSecundarioText({ angulo_esquina: "SO" })).toBe("Esquina: SO");
  });

  it("strings vacíos no generan línea", () => {
    expect(buildEstablecimientoSecundarioText({ nombre_fantasia: "  ", angulo_esquina: "" })).toBeNull();
  });

  it("bloque PDF no contiene null ni undefined", () => {
    const bloque = buildBloqueDireccionOperativaPdf({
      domicilio_texto: "San Martín Y Maipú",
      rubro_nombre: "Carnicería",
    });
    expect(bloque).not.toMatch(/null|undefined/i);
  });
});
