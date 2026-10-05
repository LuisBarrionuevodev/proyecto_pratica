import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const read = (rel: string) => readFileSync(resolve(process.cwd(), rel), "utf8");

describe("indicadores PDF export contract", () => {
  it("downloadDashboardPdf formatea período institucional", () => {
    const src = read("src/documentos/dashboard/downloadDashboardPdf.tsx");
    expect(src).toContain("Período:");
    expect(src).toContain("formatExportDatePreview(options.desde)");
  });

  it("Panel pasa mismo indicadoresParams al PDF", () => {
    const panel = read("src/Containers/Dashboard/Components/Panel.tsx");
    expect(panel).toContain("desde: indicadoresParams.desde");
    expect(panel).toContain("hasta: indicadoresParams.hasta");
    expect(panel).toContain("distrito_id: indicadoresParams.distrito_id");
    expect(panel).toContain("inspector_id: indicadoresParams.inspector_id");
  });
});
