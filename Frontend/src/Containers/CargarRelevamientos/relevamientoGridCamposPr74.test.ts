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

describe("CargarRelevamientos grid PR9.4 — sin columna Fecha", () => {
  it("no incluye columna Fecha y la primera columna es Inspector", () => {
    const ids = COLUMN_DEFINITIONS.map((c) => c.id);
    expect(ids).not.toContain("Fecha");
    expect(ids[0]).toBe("Inspector");
  });

  it("payload de grilla no incluye Fecha al extraer columnas de datos", () => {
    const row = {
      Inspector: "Inspector Uno",
      Calle: "Maipú",
      Numero: "100",
      Rubro: "Panadería",
      _rowId: "row_test",
    };
    const { Fecha, ...data } = row as Record<string, unknown>;
    expect(Fecha).toBeUndefined();
    expect(data).toMatchObject({
      Inspector: "Inspector Uno",
      Calle: "Maipú",
      Numero: "100",
      Rubro: "Panadería",
    });
  });
});
