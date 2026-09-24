import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const baseDir = fileURLToPath(new URL(".", import.meta.url));
const tablePath = resolve(baseDir, "Components/TableActuaciones.tsx");
const containerPath = resolve(baseDir, "ActuacionesContainer.tsx");

describe("DOCS-EXP.2 — export Actuaciones", () => {
  it("no muestra TablaExportButtons MRT cuando hay paginación server", () => {
    const src = readFileSync(tablePath, "utf8");
    expect(src).toContain("if (listadoServidor)");
    expect(src).toMatch(/listadoServidor[\s\S]*return null/);
  });

  it("mantiene export dataset completo en listado principal", () => {
    const src = readFileSync(containerPath, "utf8");
    expect(src).toContain("exportActuacionesDataset");
    expect(src).toContain("buildActuacionesExportFiltersFromMeta");
    expect(src).toContain("actuacionesExportToolbar");
    expect(src).toContain("exportToolbar={actuacionesExportToolbar}");
  });
});
