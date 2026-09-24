import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const read = (rel: string) => readFileSync(resolve(process.cwd(), rel), "utf8");

describe("HOTFIX-UI-LAYOUT — Urgentes/Pool sin encimar", () => {
  it("planificación 7C usa sidebar unificado con tabs (sin columna derecha dual)", () => {
    const view = read("src/Containers/RutasTrabajo/planificacion/PlanificacionView.tsx");
    const sidebar = read("src/Containers/RutasTrabajo/planificacion/PlanificacionSidebarPanel.tsx");
    expect(view).toContain("PlanificacionSidebarPanel");
    expect(sidebar).toContain("planificacionSidebarShellSx");
    expect(view).not.toContain("planificacionRightColumnSx");
    expect(view).not.toContain("planificacionUrgentesSlotSx");
  });

  it("paneles usan patrón column + list viewport + fixed sections", () => {
    const urgentes = read("src/Containers/RutasTrabajo/planificacion/UrgentesPanel.tsx");
    const pool = read("src/Containers/RutasTrabajo/planificacion/PoolDelDiaPanel.tsx");
    expect(urgentes).toContain("planificacionPanelColumnSx");
    expect(urgentes).toContain("planificacionUrgentesListViewportSx");
    expect(urgentes).toContain("planificacionFixedSectionSx");
    expect(pool).toContain("planificacionPoolListViewportSx");
    expect(pool).toContain("Continuar a asignación");
    expect(pool).toContain("planificacionFixedSectionSx");
  });

  it("pool tiene maxHeight propio y Urgentes minHeight garantizado", () => {
    const styles = read("src/Containers/RutasTrabajo/styles/institutionalVisual.ts");
    expect(styles).toContain('flex: "0 0 auto"');
    expect(styles).toContain("maxHeight");
    expect(styles).toContain('flex: "1 1 0"');
    expect(styles).toContain("planificacionUrgentesListViewportSx");
  });

  it("solo listas internas tienen overflowY auto", () => {
    const urgentes = read("src/Containers/RutasTrabajo/planificacion/UrgentesPanel.tsx");
    const pool = read("src/Containers/RutasTrabajo/planificacion/PoolDelDiaPanel.tsx");
    expect(urgentes).toContain("planificacionUrgentesListViewportSx");
    expect(pool).toContain("planificacionPoolListViewportSx");
    expect(urgentes).not.toMatch(/Stack[\s\S]*overflow:\s*"auto"/);
  });
});

describe("HOTFIX-UI-LAYOUT — Sidebar scrollbar", () => {
  it("StyleListItems recibe open y oculta scrollbar en collapsed", () => {
    const nav = read("src/Componets/NavLeft.tsx");
    const styles = read("src/styles/NavBarStyles.ts");
    expect(nav).toContain("StyleListItems(open)");
    expect(styles).toContain("scrollbarWidth: \"none\"");
    expect(styles).toContain("display: \"none\"");
  });

  it("expanded usa scrollbar fino oscuro", () => {
    const styles = read("src/styles/NavBarStyles.ts");
    expect(styles).toContain("rgba(255,255,255,0.22)");
    expect(styles).toContain("background: \"transparent\"");
  });

  it("drawer paper no scrollea (overflow hidden)", () => {
    const styles = read("src/styles/NavBarStyles.ts");
    expect(styles).toContain('overflow: "hidden"');
    expect(styles).toContain('overflowX: "hidden"');
  });

  it("lista nav tiene overflowX hidden", () => {
    const styles = read("src/styles/NavBarStyles.ts");
    expect(styles).toContain('overflowX: "hidden"');
  });
});
