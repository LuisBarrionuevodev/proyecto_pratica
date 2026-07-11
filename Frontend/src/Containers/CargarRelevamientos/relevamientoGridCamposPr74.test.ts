import { describe, expect, it } from "vitest";

import { COLUMN_DEFINITIONS } from "./config/columnDefinitions";
import { getDropdownOptions } from "../CargarActuaciones/config/dropdownOptions";
import { humanizeRelevamientoColumnLabel } from "./utils/relevamientoGridUxMessages";

const emptyCatalogs = {
  inspectores: [],
  motivos: [],
  rubros: [],
  tipos: [],
  contraproducencias: [],
  motivosComprobacion: [],
};

describe("CargarRelevamientos grid PR7.4", () => {
  it("incluye columnas Nombre fantasía y Ángulo esquina", () => {
    const ids = COLUMN_DEFINITIONS.map((c) => c.id);
    expect(ids).toContain("Nombre fantasía");
    expect(ids).toContain("Ángulo esquina");
    const nf = COLUMN_DEFINITIONS.find((c) => c.id === "Nombre fantasía");
    const ang = COLUMN_DEFINITIONS.find((c) => c.id === "Ángulo esquina");
    expect(nf?.cellType).toBe("text");
    expect(ang?.cellType).toBe("dropdown");
  });

  it("dropdown Ángulo esquina ofrece NE/NO/SE/SO", () => {
    expect(getDropdownOptions("Ángulo esquina", emptyCatalogs)).toEqual(["", "NE", "NO", "SE", "SO"]);
  });

  it("humaniza etiquetas de columnas nuevas", () => {
    expect(humanizeRelevamientoColumnLabel("Nombre fantasía")).toBe("Nombre fantasía");
    expect(humanizeRelevamientoColumnLabel("Ángulo esquina")).toBe("Ángulo esquina");
  });
});
