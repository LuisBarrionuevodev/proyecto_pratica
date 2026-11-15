import { describe, expect, it } from "vitest";

import {
  CORRECCION_CONTRIBUYENTE_HINT,
  CORRECCION_DOMICILIO_HINT,
  CORRECCION_LOCAL_HINT,
  CORRECCION_SIN_CAMBIOS_HINT,
  VINCULACION_ACCION,
  VINCULACION_DOCUMENTO_AJENO_CTA,
  VINCULACION_HINT,
  inferTitularCorreccionModo,
} from "./correccionEstablecimientoCopy";

describe("correccionEstablecimientoCopy", () => {
  it("no promete recálculo de coordenadas ni cambio de titular", () => {
    expect(CORRECCION_CONTRIBUYENTE_HINT.toLowerCase()).toContain("mismo contribuyente");
    expect(CORRECCION_CONTRIBUYENTE_HINT.toLowerCase()).toContain("no cambia el titular");
    expect(CORRECCION_CONTRIBUYENTE_HINT.toLowerCase()).toContain("ni fusiona");
    expect(CORRECCION_DOMICILIO_HINT.toLowerCase()).toContain("no se recalculan coordenadas");
    expect(CORRECCION_SIN_CAMBIOS_HINT.toLowerCase()).toContain("no se desvincula");
    expect(CORRECCION_LOCAL_HINT.toLowerCase()).toContain("este establecimiento");
    expect(CORRECCION_LOCAL_HINT.toLowerCase()).toContain("no modifica otros locales");
  });

  it("infiere persona, razón social o ambos sin perder datos", () => {
    expect(
      inferTitularCorreccionModo({ apellido: "Pérez", nombre: "Ana", razonSocial: "" })
    ).toBe("persona");
    expect(
      inferTitularCorreccionModo({ apellido: "", nombre: "", razonSocial: "Panadería SRL" })
    ).toBe("razon_social");
    expect(
      inferTitularCorreccionModo({
        apellido: "Pérez",
        nombre: "Ana",
        razonSocial: "Panadería SRL",
      })
    ).toBe("ambos");
    expect(inferTitularCorreccionModo({ apellido: "", nombre: "", razonSocial: "" })).toBe(
      "persona"
    );
  });

  it("vinculación no promete editar datos personales ni fusionar", () => {
    expect(VINCULACION_HINT.toLowerCase()).toContain("vínculo");
    expect(VINCULACION_HINT.toLowerCase()).toContain("no edita");
    expect(VINCULACION_ACCION).toBe("Vincular este establecimiento");
    expect(VINCULACION_DOCUMENTO_AJENO_CTA.toLowerCase()).toContain("no cambia el titular");
  });
});
