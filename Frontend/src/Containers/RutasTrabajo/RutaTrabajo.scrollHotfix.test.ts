import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const read = (rel: string) => readFileSync(resolve(process.cwd(), rel), "utf8");

describe("Scroll hotfix — Ruta de Trabajo panel derecho", () => {
  it("1. panel derecho tiene body scrolleable con padding inferior", () => {
    const styles = read("src/Containers/RutasTrabajo/styles/institutionalVisual.ts");
    const urgentes = read("src/Containers/RutasTrabajo/planificacion/UrgentesPanel.tsx");
    const pool = read("src/Containers/RutasTrabajo/planificacion/PoolDelDiaPanel.tsx");
    expect(styles).toContain("planificacionListBodySx");
    expect(styles).toContain('flex: "1 1 0"');
    expect(styles).toContain("planificacionListScrollSafeSx");
    expect(urgentes).toContain('className="planificacion-list-body"');
    expect(pool).toContain('className="planificacion-list-body"');
  });

  it("2. footer/paginación está fuera del body scrolleable y visible", () => {
    const styles = read("src/Containers/RutasTrabajo/styles/institutionalVisual.ts");
    const urgentes = read("src/Containers/RutasTrabajo/planificacion/UrgentesPanel.tsx");
    const pool = read("src/Containers/RutasTrabajo/planificacion/PoolDelDiaPanel.tsx");
    expect(styles).toContain("planificacionPanelFooterSx");
    expect(urgentes).toContain('className="planificacion-pagination-footer"');
    expect(urgentes).toContain("Anterior");
    expect(urgentes).toContain("Siguiente");
    expect(pool).toContain('className="planificacion-panel-footer"');
    expect(pool).toContain("Continuar a asignación");
  });

  it("3. último item no queda tapado por footer", () => {
    const pool = read("src/Containers/RutasTrabajo/planificacion/PoolDelDiaPanel.tsx");
    const urgentes = read("src/Containers/RutasTrabajo/planificacion/UrgentesPanel.tsx");
    expect(pool).not.toContain('"&:last-of-type": { borderBottom: "none", pb: 0 }');
    expect(pool).toContain('pb: 0.5');
    expect(urgentes).toContain('pb: 0.5');
    expect(urgentes).toContain("planificacionPanelFooterSx");
  });

  it("4. slots flex y overflow solo en listas internas", () => {
    const sidebar = read("src/Containers/RutasTrabajo/planificacion/PlanificacionSidebarPanel.tsx");
    const layout = read("src/Containers/RutasTrabajo/planificacion/planificacionMyMapsLayout.ts");
    expect(sidebar).toContain("planificacionSidebarTabBodySx");
    expect(layout).toContain('overflowY: "auto"');
    expect(layout).not.toContain('minHeight: "16rem"');
  });
});
