import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const baseDir = fileURLToPath(new URL(".", import.meta.url));

describe("IND-EXP.1 — Relevamientos sin export", () => {
  it("TableRelevamientos no muestra TablaExportButtons", () => {
    const src = readFileSync(resolve(baseDir, "Components/TableRelevamientos.tsx"), "utf8");
    expect(src).toContain("MaterialReactTable");
    expect(src).not.toContain("TablaExportButtons");
    expect(src).not.toContain("renderTopToolbarCustomActions");
  });
});

describe("IND-EXP.1 — Denuncias sin export", () => {
  it("TableDenuncias no muestra TablaExportButtons", () => {
    const src = readFileSync(resolve(baseDir, "Components/TableDenuncias.tsx"), "utf8");
    expect(src).toContain("MaterialReactTable");
    expect(src).not.toContain("TablaExportButtons");
    expect(src).not.toContain("renderTopToolbarCustomActions");
  });
});
