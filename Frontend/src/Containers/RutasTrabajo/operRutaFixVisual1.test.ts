import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const read = (rel: string) => readFileSync(resolve(process.cwd(), rel), "utf8");

describe("RUTAS / FIX VISUAL 1 — chips y botones destructivos", () => {
  it("Pool de la ruta usa Quitar destructivo y chips unificados", () => {
    const strip = read("src/Containers/RutasTrabajo/planificacion/PlanificacionPoolCardsStrip.tsx");
    expect(strip).toContain('dsVariant="danger"');
    expect(strip).toContain("RutasOperativaChip");
    expect(strip).not.toContain('dsVariant="ghost"');
  });

  it("PanelGruposRuta y resumen usan RutasOperativaChip", () => {
    const panel = read("src/Containers/RutasTrabajo/Components/PanelGruposRuta.tsx");
    expect(panel).toContain("RutasOperativaChip");
    expect(panel).toContain('dsVariant="danger"');
    const resumen = read("src/Containers/RutasTrabajo/Components/AsignacionGruposResumenChips.tsx");
    expect(resumen).toContain("RutasOperativaChip");
    expect(resumen).not.toContain("fontWeight: 600");
  });

  it("estilo compartido rutasOperativaChipSx en institutionalVisual", () => {
    const styles = read("src/Containers/RutasTrabajo/styles/institutionalVisual.ts");
    expect(styles).toContain("rutasOperativaChipSx");
    expect(styles).toContain("fontWeight: 700");
  });

  it("Tabla asignación eliminar del pool usa danger estándar", () => {
    const tabla = read("src/Containers/RutasTrabajo/Components/TablaIniciadoresPendientes.tsx");
    expect(tabla).toContain('dsVariant="danger"');
    expect(tabla).not.toContain('bgcolor: "error.main"');
  });

  it("Tabla asignación contador seleccionados usa RutasOperativaChip", () => {
    const tabla = read("src/Containers/RutasTrabajo/Components/TablaIniciadoresPendientes.tsx");
    expect(tabla).toContain("RutasOperativaChip");
    expect(tabla).toContain("${nSel} seleccionados");
    expect(tabla).not.toMatch(/<Chip label=\{\`\$\{nSel\} seleccionados\`\}/);
  });
});
