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

  it("bloque orden salida: domicilio y ángulo sin rubro ni fantasía", () => {
    const bloque = buildBloqueDireccionOperativaPdf({
      domicilio_texto: "San Martín Y Maipú",
      rubro_nombre: "Carnicería",
      nombre_fantasia: "El Toro",
      angulo_esquina: "NE",
    });
    expect(bloque).toBe("San Martín Y Maipú\nÁngulo: NE");
    expect(bloque).not.toContain("Carnicería");
    expect(bloque).not.toContain("fantasía");
  });

  it("bloque orden salida: solo domicilio calle+número", () => {
    const bloque = buildBloqueDireccionOperativaPdf({
      domicilio_texto: "Maipú 500",
      rubro_nombre: "Panadería",
    });
    expect(bloque).toBe("Maipú 500");
    expect(bloque).not.toContain("null");
    expect(bloque).not.toContain("undefined");
  });
});
