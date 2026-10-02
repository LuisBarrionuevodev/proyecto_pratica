import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const read = (rel: string) => readFileSync(resolve(process.cwd(), rel), "utf8");

describe("HOTFIX V1.1-OPER.1A — grid kind en requests", () => {
  const gridApi = read("src/api/gridApi.ts");
  const relevGlide = read(
    "src/Containers/CargarRelevamientos/Components/TablaCargarRelevamientosGlideStyled.tsx"
  );
  const actGlide = read(
    "src/Containers/CargarActuaciones/Components/TablaCargarActuacionesGlideStyled.tsx"
  );

  it("gridApi exige kind en validate/commit", () => {
    expect(gridApi).toContain("kind: GridBatchKind");
    expect(gridApi).toContain('export type GridBatchKind = "actuaciones" | "relevamientos"');
  });

  it("Cargar Relevamientos envía kind relevamientos en validate y commit", () => {
    expect(relevGlide).toContain('const GRID_KIND = "relevamientos"');
    expect(relevGlide).toContain("kind: GRID_KIND");
    expect(relevGlide).toMatch(/validateBatch\(\{[\s\S]*kind: GRID_KIND/);
    expect(relevGlide).toMatch(/commitBatch\(\{[\s\S]*kind: GRID_KIND/);
  });

  it("Cargar Actuaciones envía kind actuaciones en validate y commit", () => {
    expect(actGlide).toContain('const GRID_KIND = "actuaciones"');
    expect(actGlide).toContain("kind: GRID_KIND");
    expect(actGlide).toMatch(/validateBatch\(\{[\s\S]*kind: GRID_KIND/);
    expect(actGlide).toMatch(/commitBatch\(\{[\s\S]*kind: GRID_KIND/);
  });
});
