import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const read = (rel: string) => readFileSync(resolve(process.cwd(), rel), "utf8");

describe("V1.1-RESP.4 — dashboard mobile-first", () => {
  it("Panel usa tabs responsive y franja compacta de filtros", () => {
    const panel = read("src/Containers/Dashboard/Components/Panel.tsx");
    expect(panel).toContain('data-testid="dashboard-panel"');
    expect(panel).toContain('data-testid="dashboard-indicadores-toolbar"');
    expect(panel).toContain("ResponsiveScrollableTabs");
    expect(panel).toContain("IndicadoresMonthPickerDialog");
    expect(panel).toContain("useIndicadoresFiltros");
    expect(panel).toContain('overflowX: "hidden"');
    expect(panel).not.toContain("<Tabs");
    expect(panel).not.toContain('fullWidth');
  });

  it("KPI grids: una columna en xs", () => {
    const metric = read("src/Containers/Dashboard/Components/DashboardMetricGrid.tsx");
    expect(metric).toContain('xs: "1fr"');
    const exec = read("src/Containers/Dashboard/Components/DashboardExecutiveKpiGrid.tsx");
    expect(exec).toContain('xs: "1fr"');
  });

  it("charts y tablas con contención horizontal", () => {
    const chartCard = read("src/Containers/Dashboard/Components/DashboardAnalyticsChartCard.tsx");
    expect(chartCard).toContain('overflowX: "auto"');
    const prod = read("src/Containers/Dashboard/Components/DashboardProductividadSection.tsx");
    expect(prod).toContain("overflowX: \"auto\"");
    expect(prod).toContain('minWidth: 0');
  });

  it("no expone controles Desde/Hasta ni sección Tendencias en Panel", () => {
    const panel = read("src/Containers/Dashboard/Components/Panel.tsx");
    expect(panel).not.toContain("DashboardTendenciasSection");
    expect(panel).not.toContain("label=\"Desde\"");
    expect(panel).not.toContain("label=\"Hasta\"");
  });

  it("mantiene exportación PDF y hooks de indicadores", () => {
    const panel = read("src/Containers/Dashboard/Components/Panel.tsx");
    expect(panel).toContain("Exportar PDF");
    expect(panel).toContain("downloadDashboardPdf");
    expect(panel).toContain("indicadoresParams");
    expect(panel).toContain("indicadoresParams.desde");
    expect(panel).toContain("Elegir mes");
  });

  it("tabs limpian override mensual al cambiar período", () => {
    const hook = read("src/Containers/Dashboard/hooks/useIndicadoresFiltros.ts");
    expect(hook).toContain("setMonthOverride(null)");
    expect(hook).toContain("setPeriodoState(next)");
  });
});
