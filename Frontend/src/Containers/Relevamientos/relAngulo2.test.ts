import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { COLUMN_DEFINITIONS, RELEVAMIENTO_COLUMN_HEADER_TOOLTIPS } from "../CargarRelevamientos/config/columnDefinitions";
import { getDropdownOptions } from "../CargarActuaciones/config/dropdownOptions";
import { buildNumeroTipoDraftPatch, relevamientoRowParaEdicion } from "./utils/relevamientoCamposForm";
import { normalizeRelevamientoRowForApi } from "./utils/submitRelevamientoRow";

const root = resolve(__dirname, "../..");

function read(rel: string): string {
  return readFileSync(resolve(root, rel), "utf8");
}

const emptyCatalogs = {
  relevadores: [],
  motivos: [],
  rubros: [],
  tipos: [],
  contraproducencias: [],
  motivosComprobacion: [],
};

describe("REL-ANGULO.2 — UX número/esquina y orientación", () => {
  it("Cargar: headers nuevos sin cambiar ids de columna", () => {
    const numero = COLUMN_DEFINITIONS.find((c) => c.id === "Numero");
    const orientacion = COLUMN_DEFINITIONS.find((c) => c.id === "Ángulo esquina");
    expect(numero?.title).toBe("Número / esquina");
    expect(orientacion?.title).toBe("Orientación");
    expect(orientacion?.id).toBe("Ángulo esquina");
  });

  it("Cargar: dropdown Orientación conserva NE/NO/SE/SO", () => {
    expect(getDropdownOptions("Ángulo esquina", emptyCatalogs)).toEqual(["", "NE", "NO", "SE", "SO"]);
  });

  it("Cargar: tooltips de ayuda para número y orientación", () => {
    expect(RELEVAMIENTO_COLUMN_HEADER_TOOLTIPS.Numero).toContain("altura");
    expect(RELEVAMIENTO_COLUMN_HEADER_TOOLTIPS["Ángulo esquina"]).toContain("NE, NO, SE o SO");
    const gridSrc = read("Containers/CargarRelevamientos/Components/TablaCargarRelevamientosGlideStyled.tsx");
    expect(gridSrc).toContain("RELEVAMIENTO_COLUMN_HEADER_TOOLTIPS");
  });

  it("NUMERO no persiste orientación en payload", () => {
    const out = normalizeRelevamientoRowForApi({
      id: 1,
      fecha: "2026-05-10",
      inspector: "X",
      calle: "Maipú",
      numero: "100",
      numero_tipo: "NUMERO",
      rubro: "Carnicería",
      angulo_esquina: "NE",
    } as any);
    expect(out.angulo_esquina).toBeNull();
  });

  it("ESQUINA persiste orientación normalizada", () => {
    const out = normalizeRelevamientoRowForApi({
      id: 1,
      fecha: "2026-05-10",
      inspector: "X",
      calle: "Maipú",
      numero: "Salta",
      numero_tipo: "ESQUINA",
      rubro: "Carnicería",
      angulo_esquina: "so",
    } as any);
    expect(out.angulo_esquina).toBe("SO");
  });

  it("ESQUINA → NUMERO limpia orientación al cambiar tipo", () => {
    const patch = buildNumeroTipoDraftPatch("NUMERO", {
      numero_tipo: "ESQUINA",
      numero: "Belgrano",
      angulo_esquina: "NE",
    } as any);
    expect(patch.angulo_esquina).toBeNull();
  });

  it("Gestión: RelevamientoCrudDialog usa Orientación y labels por modo", () => {
    const src = read("Containers/Relevamientos/Components/RelevamientoCrudDialog.tsx");
    expect(src).toContain('label="Orientación"');
    expect(src).toContain('"Calle de esquina"');
    expect(src).toContain("NumeroEsquinaEditor");
  });

  it("Gestión: hidrata fila para edición", () => {
    const hydrated = relevamientoRowParaEdicion({
      id: 3,
      fecha: "2026-05-10",
      calle: "San Martín",
      calle_estado: "OK",
      calle_normalizada: "Av. San Martín",
      numero: "450",
      numero_tipo: "NUMERO",
      rubro: "Panadería",
      angulo_esquina: null,
    } as any);
    expect(hydrated.calle).toBe("Av. San Martín");
    expect(hydrated.numero).toBe("450");
  });

  it("TAB navigation sigue usando util canónico", () => {
    const src = read("Containers/CargarRelevamientos/Components/TablaCargarRelevamientosGlideStyled.tsx");
    expect(src).toContain("resolveRelevamientoTabForwardStep");
    expect(src).toContain("relevamientoResolveTabDataCol");
  });
});
