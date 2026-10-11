import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

import { validationRailHasContent } from "./Components/ValidationErrorsRail";
import { resolveRelevadorIdsFromNombres } from "./utils/relevamientoRelevadorCell";

const baseDir = resolve(import.meta.dirname);

function read(rel: string): string {
  return readFileSync(resolve(baseDir, rel), "utf8");
}

describe("V1.1-CATALOGOS-UX.1 carga relevamientos", () => {
  it("no muestra rail de errores vacío", () => {
    expect(validationRailHasContent(null, [])).toBe(false);
    expect(read("Components/TablaCargarRelevamientosGlideStyled.tsx")).toContain("showValidationRail");
    expect(read("Components/TablaCargarRelevamientosGlideStyled.tsx")).not.toContain('flexDirection: { xs: "column", lg: "row" }');
  });

  it("resuelve relevador legacy y etiqueta Apellido, Nombre", () => {
    const catalog = [{ id: 7, nombre: "Esquivel, Fabian" }];
    expect(resolveRelevadorIdsFromNombres(["Fabian Esquivel"], catalog)).toEqual([7]);
    expect(resolveRelevadorIdsFromNombres(["Esquivel, Fabian"], catalog)).toEqual([7]);
  });
});

describe("V1.1 contraste comprobación oficios", () => {
  it("cards oficio usan tokens de tema", () => {
    const section = readFileSync(
      resolve(baseDir, "../ActasComprobacion/components/ComprobacionOficiosTribunalSection.tsx"),
      "utf8"
    );
    expect(section).toContain("comprobacionOficioOperativoCardSx");
    expect(section).not.toContain("rgba(255,255,255,0.92)");
    const tokens = readFileSync(resolve(baseDir, "../../styles/documentalModalTokens.ts"), "utf8");
    expect(tokens).toContain("theme.palette.text.primary");
  });
});
