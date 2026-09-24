import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const tablePath = resolve(
  fileURLToPath(new URL(".", import.meta.url)),
  "Components/TableDenuncias.tsx"
);

describe("IND-EXP.1 — Denuncias sin export", () => {
  it("no muestra TablaExportButtons y mantiene tabla", () => {
    const src = readFileSync(tablePath, "utf8");
    expect(src).toContain("MaterialReactTable");
    expect(src).toContain("DenunciaCrudDialog");
    expect(src).not.toContain("TablaExportButtons");
    expect(src).not.toContain("renderTopToolbarCustomActions");
  });
});
