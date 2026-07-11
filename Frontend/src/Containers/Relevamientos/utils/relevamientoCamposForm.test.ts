import { describe, expect, it } from "vitest";

import {
  applyEstablecimientoCamposToPayload,
  buildNumeroTipoDraftPatch,
  detectNumeroLooksLikeEsquina,
  normalizarAnguloEsquinaFrontend,
  normalizarNombreFantasiaFrontend,
  NOMBRE_FANTASIA_MAX_LEN,
  relevamientoAnguloEsAplicable,
} from "./relevamientoCamposForm";

describe("relevamientoCamposForm", () => {
  it("normaliza nombre fantasía con trim y máximo 255", () => {
    expect(normalizarNombreFantasiaFrontend("  El Toro  ")).toBe("El Toro");
    expect(normalizarNombreFantasiaFrontend("")).toBeNull();
    expect(normalizarNombreFantasiaFrontend("   ")).toBeNull();
    const long = "a".repeat(NOMBRE_FANTASIA_MAX_LEN + 10);
    expect(normalizarNombreFantasiaFrontend(long)?.length).toBe(NOMBRE_FANTASIA_MAX_LEN);
  });

  it("detecta número con forma de esquina", () => {
    expect(detectNumeroLooksLikeEsquina("Belgrano y San Martín")).toBe(true);
    expect(detectNumeroLooksLikeEsquina("123")).toBe(false);
    expect(detectNumeroLooksLikeEsquina("S/N")).toBe(false);
  });

  it("normaliza ángulo solo NE/NO/SE/SO", () => {
    expect(normalizarAnguloEsquinaFrontend("ne", { numero_tipo: "ESQUINA" }).value).toBe("NE");
    expect(normalizarAnguloEsquinaFrontend("", { numero_tipo: "ESQUINA" }).value).toBeNull();
    expect(normalizarAnguloEsquinaFrontend("XX", { numero_tipo: "ESQUINA" }).error).toBeTruthy();
    expect(
      normalizarAnguloEsquinaFrontend("NE", { numero_tipo: "NUMERO", numero: "450" }).value
    ).toBeNull();
  });

  it("relevamientoAnguloEsAplicable en ESQUINA o intersección detectada", () => {
    expect(relevamientoAnguloEsAplicable({ numero_tipo: "ESQUINA" })).toBe(true);
    expect(relevamientoAnguloEsAplicable({ numero: "Calle A y Calle B" })).toBe(true);
    expect(relevamientoAnguloEsAplicable({ numero: "123" })).toBe(false);
  });

  it("buildNumeroTipoDraftPatch limpia ángulo al pasar a NUMERO", () => {
    expect(buildNumeroTipoDraftPatch("NUMERO")).toEqual({
      numero_tipo: "NUMERO",
      angulo_esquina: null,
    });
    expect(buildNumeroTipoDraftPatch("ESQUINA")).toEqual({ numero_tipo: "ESQUINA" });
  });

  it("applyEstablecimientoCamposToPayload aplica ambos campos", () => {
    const out = applyEstablecimientoCamposToPayload({
      id: 1,
      fecha: "2026-05-01",
      inspector: "A",
      calle: "X",
      numero: "Belgrano y Mitre",
      rubro: "Panadería",
      nombre_fantasia: "  La Esquina  ",
      angulo_esquina: "so",
      numero_tipo: "ESQUINA",
    });
    expect(out.nombre_fantasia).toBe("La Esquina");
    expect(out.angulo_esquina).toBe("SO");
  });
});
