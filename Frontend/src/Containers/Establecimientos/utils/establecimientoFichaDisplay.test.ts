import { describe, expect, it } from "vitest";

import {
  ESTABLECIMIENTO_NOMBRE_LOCAL_SIN_REGISTRAR,
  establecimientoFichaContribuyenteNombre,
  establecimientoFichaDocumentoVisible,
  establecimientoFichaNombreLocalEsPlaceholder,
  establecimientoFichaNombreLocalVisible,
  establecimientoFichaRubroVisible,
} from "./establecimientoFichaDisplay";

describe("establecimientoFichaDisplay UX.1", () => {
  it("muestra persona física como nombre y apellido", () => {
    expect(
      establecimientoFichaContribuyenteNombre({
        contrib_nombre: "Ana",
        contrib_apellido: "Pérez",
        razon_social: null,
      })
    ).toBe("Ana Pérez");
  });

  it("prioriza razón social sobre persona física", () => {
    expect(
      establecimientoFichaContribuyenteNombre({
        contrib_nombre: "Ana",
        contrib_apellido: "Pérez",
        razon_social: "Panadería El Sol S.A.",
      })
    ).toBe("Panadería El Sol S.A.");
  });

  it("sin titular no inventa Establecimiento #id", () => {
    expect(
      establecimientoFichaContribuyenteNombre({
        contrib_nombre: "  ",
        contrib_apellido: null,
        razon_social: "",
      })
    ).toBe("—");
  });

  it("documento ausente usa guión", () => {
    expect(establecimientoFichaDocumentoVisible(null)).toBe("—");
    expect(establecimientoFichaDocumentoVisible("  ")).toBe("—");
    expect(establecimientoFichaDocumentoVisible("20123456789")).toBe("20123456789");
  });

  it("nombre de local vacío muestra placeholder sin usar el contribuyente", () => {
    expect(establecimientoFichaNombreLocalVisible(null)).toBe(
      ESTABLECIMIENTO_NOMBRE_LOCAL_SIN_REGISTRAR
    );
    expect(establecimientoFichaNombreLocalVisible("   ")).toBe(
      ESTABLECIMIENTO_NOMBRE_LOCAL_SIN_REGISTRAR
    );
    expect(establecimientoFichaNombreLocalVisible("Kiosco 24")).toBe("Kiosco 24");
    expect(establecimientoFichaNombreLocalEsPlaceholder(null)).toBe(true);
    expect(establecimientoFichaNombreLocalEsPlaceholder("Kiosco 24")).toBe(false);
  });

  it("rubro ausente usa guión", () => {
    expect(establecimientoFichaRubroVisible(undefined)).toBe("—");
    expect(establecimientoFichaRubroVisible("Almacén")).toBe("Almacén");
  });
});
