import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const read = (rel: string) => readFileSync(resolve(process.cwd(), rel), "utf8");

describe("OPER-RUTA.7C — layout My Maps planificación", () => {
  it("PlanificacionView usa sidebar unificado + mapa amplio (lg 4/8)", () => {
    const view = read("src/Containers/RutasTrabajo/planificacion/PlanificacionView.tsx");
    expect(view).toContain("PlanificacionSidebarPanel");
    expect(view).toContain('data-testid="planificacion-my-maps-layout"');
    expect(view).toContain('size={{ xs: 12, lg: 4 }}');
    expect(view).toContain('size={{ xs: 12, lg: 8 }}');
    expect(view).not.toContain("PlanificacionSummaryCards");
    expect(view).not.toContain("planificacionRightColumnSx");
    expect(view).not.toContain("planificacionUrgentesSlotSx");
  });

  it("sidebar panel integra filtros y tabs 7C.1", () => {
    const sidebar = read("src/Containers/RutasTrabajo/planificacion/PlanificacionSidebarPanel.tsx");
    expect(sidebar).toContain("PlanificacionFiltrosBar");
    expect(sidebar).toContain("Total mapa");
    expect(sidebar).toContain("Urgentes");
    expect(sidebar).toContain('variant="embedded"');
    expect(sidebar).not.toContain("PoolDelDiaPanel");
    expect(sidebar).not.toContain("planificacion-continuar-asignacion");
  });

  it("filtros bar muestra tipo, rubro y búsqueda compacta", () => {
    const filtros = read("src/Containers/RutasTrabajo/planificacion/PlanificacionFiltrosBar.tsx");
    expect(filtros).toContain("PlanificacionTipoFilterChips");
    expect(filtros).toContain("PlanificacionRubroSelect");
    expect(filtros).toContain("Buscar domicilio o referencia");
  });

  it("paneles soportan variant embedded sin duplicar paper", () => {
    const pendientes = read("src/Containers/RutasTrabajo/planificacion/PendientesContextoPanel.tsx");
    const urgentes = read("src/Containers/RutasTrabajo/planificacion/UrgentesPanel.tsx");
    const pool = read("src/Containers/RutasTrabajo/planificacion/PoolDelDiaPanel.tsx");
    expect(pendientes).toContain('variant?: "standalone" | "embedded"');
    expect(urgentes).toContain('variant?: "standalone" | "embedded"');
    expect(pool).toContain('variant?: "standalone" | "embedded"');
    expect(pendientes).toContain("planificacionSidebarListViewportSx");
    expect(urgentes).toContain("planificacionSidebarListViewportSx");
    expect(pool).toContain("planificacionSidebarListViewportSx");
  });

  it("listas mantienen scroll interno y paginación visible", () => {
    const urgentes = read("src/Containers/RutasTrabajo/planificacion/UrgentesPanel.tsx");
    const pool = read("src/Containers/RutasTrabajo/planificacion/PoolDelDiaPanel.tsx");
    expect(urgentes).toContain('className="planificacion-list-body"');
    expect(urgentes).toContain('className="planificacion-pagination-footer"');
    expect(pool).toContain('className="planificacion-list-body"');
    expect(urgentes).toContain("Anterior");
    expect(urgentes).toContain("Siguiente");
  });
});
