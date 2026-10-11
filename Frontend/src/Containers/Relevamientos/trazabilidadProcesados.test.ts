import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

const baseDir = resolve(import.meta.dirname);

function read(rel: string): string {
  return readFileSync(resolve(baseDir, rel), "utf8");
}

describe("V1.1 bandeja Procesados (Relevamientos / Denuncias)", () => {
  it("pestaña Procesados en relevamientos y denuncias", () => {
    expect(read("RelevamientosContainer.tsx")).toContain('label="Procesados"');
    expect(read("RelevamientosContainer.tsx")).toContain('value="procesados"');
    expect(read("Components/DenunciasCrudPlaceholder.tsx")).toContain('label="Procesados"');
  });

  it("hooks consumen endpoints procesados", () => {
    expect(read("hooks/useRelevamientosBandeja.ts")).toContain("getRelevamientosProcesadosFiltered");
    expect(read("hooks/useDenunciasBandeja.ts")).toContain("getDenunciasGestionProcesados");
  });

  it("columna/chip Resultado", () => {
    expect(read("utils/resultadoProcesadoColumn.tsx")).toContain('header: "Resultado"');
    expect(read("Components/ResultadoProcesadoChip.tsx")).toContain("NO_EXISTE_LOCAL");
    expect(read("Components/TableDenuncias.tsx")).toContain("showResultadoProcesado");
  });

  it("empty states procesados", () => {
    expect(read("RelevamientosContainer.tsx")).toContain("No hay relevamientos procesados.");
    expect(read("Components/DenunciasCrudPlaceholder.tsx")).toContain("No hay denuncias procesadas.");
  });

  it("vista móvil: acciones ver en procesados denuncias", () => {
    const table = read("Components/TableDenuncias.tsx");
    expect(table).toContain("enableRowActions: true");
    expect(table).toContain("VisibilityIcon");
  });
});
