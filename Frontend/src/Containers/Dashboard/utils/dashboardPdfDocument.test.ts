import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

import type { DashboardExportPayload } from "./buildDashboardExportPayload";
import { buildDashboardPdfModel } from "./dashboardPdfMappers";

const emptyPayload: DashboardExportPayload = {
  meta: { periodoLabel: "", distritoLabel: "Todos", inspectorLabel: "Todos" },
  resumenKpis: [],
  ejecutivo: null,
  pendientes: null,
  actasPorTipo: null,
  pendientesDistritos: [],
  riesgo: null,
  mercaderiaDecomisadaKg: null,
  noRealizadas: null,
  noRealizadasTotal: null,
  productividad: null,
};

const rendererPath = resolve(
  fileURLToPath(new URL(".", import.meta.url)),
  "../../../documentos/renderers/DashboardIndicadoresPdfDocument.tsx"
);

describe("DashboardIndicadoresPdfDocument", () => {
  it("renderiza título, período, filtros y secciones principales", () => {
    const src = readFileSync(rendererPath, "utf8");
    expect(src).toContain("model.title");
    expect(src).toContain("model.periodoLine");
    expect(src).toContain("model.distritoLabel");
    expect(src).toContain("model.inspectorLabel");
    expect(src).toContain("Resumen ejecutivo");
    expect(src).toContain("Pendientes operativos");
    expect(src).toContain("Actas por tipo");
    expect(src).toContain("Riesgo bromatológico");
    expect(src).toContain("No realizadas");
    expect(src).not.toContain("Por tipo operativo");
    expect(src).toContain("Productividad");
    expect(src).toContain("DASHBOARD_PDF_EMPTY_MESSAGE");
  });
});

describe("dashboardPdfMappers title", () => {
  it("define título institucional del informe", () => {
    const model = buildDashboardPdfModel(
      emptyPayload,
      "2026-01-01",
      "2026-01-31",
      "04/08/2026",
      "01/01/2026 al 31/01/2026"
    );
    expect(model.title).toBe("Informe de Indicadores Operativos");
  });
});
