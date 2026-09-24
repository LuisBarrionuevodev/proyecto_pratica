import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const baseDir = fileURLToPath(new URL(".", import.meta.url));

const pendientesTables = [
  "Containers/Pendientes/Components/TablaPendientes.tsx",
  "Containers/PendientesVinculacionActa/Components/TablaPendientesVinculacionActa.tsx",
  "Containers/PendientesVinculacionOficio/Components/TablaPendientesVinculacionOficio.tsx",
];

describe("IND-EXP.1 — Pendientes sin export MRT", () => {
  it.each(pendientesTables)("%s no usa TablaExportButtons", (relPath) => {
    const src = readFileSync(resolve(baseDir, relPath), "utf8");
    expect(src).toContain("MaterialReactTable");
    expect(src).not.toContain("TablaExportButtons");
    expect(src).not.toContain("renderTopToolbarCustomActions");
  });

  it("TablaPendientesVinculacionActa mantiene acciones operativas", () => {
    const src = readFileSync(
      resolve(baseDir, "Containers/PendientesVinculacionActa/Components/TablaPendientesVinculacionActa.tsx"),
      "utf8"
    );
    expect(src).toContain("AppDialog");
    expect(src).toContain("updateActuacion");
  });

  it("TablaPendientesVinculacionOficio mantiene modal operativo", () => {
    const src = readFileSync(
      resolve(baseDir, "Containers/PendientesVinculacionOficio/Components/TablaPendientesVinculacionOficio.tsx"),
      "utf8"
    );
    expect(src).toContain("BasicModal");
    expect(src).toContain("CardsExpedientes");
  });
});
