import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const read = (rel: string) => readFileSync(resolve(process.cwd(), rel), "utf8");

describe("OPER-RUTA.7C.3 — pool strip + header derecha + altura real", () => {
  it("header compacto alinea acciones a la derecha sin chips centrales", () => {
    const header = read("src/Containers/RutasTrabajo/Components/RutaTrabajoCompactHeader.tsx");
    expect(header).toContain('data-testid="ruta-trabajo-header-actions"');
    expect(header).toContain("flexGrow: 1");
    expect(header).toContain('justifyContent: { xs: "flex-start", md: "flex-end" }');
    expect(header).not.toContain("RutaResumenHeaderCard");
    expect(header).not.toContain("turnoLabel");
    expect(header).not.toContain("itemsSinOtHint");
  });

  it("Planificación renderiza strip Pool de la ruta con contexto en título", () => {
    const view = read("src/Containers/RutasTrabajo/planificacion/PlanificacionView.tsx");
    expect(view).toContain("PlanificacionPoolCardsStrip");
    expect(view).toContain("buildPlanificacionPoolStripItems");
    expect(view).not.toContain("PoolDelDiaPanel");
    expect(view).not.toContain("Continuar a asignación");
    const strip = read("src/Containers/RutasTrabajo/planificacion/PlanificacionPoolCardsStrip.tsx");
    expect(strip).toContain('data-testid="planificacion-pool-strip"');
    expect(strip).toContain("Pool de la ruta");
    expect(strip).toContain("RutaContextoLine");
    expect(strip).toContain('data-testid="planificacion-pool-strip-empty"');
    expect(strip).toContain("Quitar");
  });

  it("Asignación muestra contexto junto al título del pool del día", () => {
    const asignacion = read("src/Containers/RutasTrabajo/views/RutasPlanificacionView.tsx");
    expect(asignacion).toContain("Ítems del pool del día");
    expect(asignacion).toContain("RutaContextoLine");
  });

  it("index avisa OT sin guardar vía toast global en asignación", () => {
    const index = read("src/Containers/RutasTrabajo/index.tsx");
    expect(index).toContain("sin OT guardada");
    expect(index).toContain("feedback.warning");
    expect(index).not.toContain("itemsSinOtHint");
  });

  it("layout main area usa calc viewport y listado flexible", () => {
    const layout = read("src/Containers/RutasTrabajo/planificacion/planificacionMyMapsLayout.ts");
    expect(layout).toContain("planificacionMainAreaSx");
    expect(layout).toContain("calc(100vh -");
    expect(layout).toContain("PLANIFICACION_MAIN_AREA_MIN_HEIGHT_PX");
    const pendientes = read("src/Containers/RutasTrabajo/planificacion/PendientesContextoPanel.tsx");
    expect(pendientes).toContain('data-testid="planificacion-sidebar-flex-list"');
    const mapa = read("src/Containers/RutasTrabajo/planificacion/PlanificacionMapaDistritos.tsx");
    expect(mapa).toContain('height: "100%"');
    expect(mapa).not.toContain("maxHeight: PLANIFICACION_MY_MAPS_HEIGHT");
  });

  it("pines rojos siguen presentes junto al pool strip", () => {
    const view = read("src/Containers/RutasTrabajo/planificacion/PlanificacionView.tsx");
    expect(view).toContain("buildPlanificacionUsedMarkers");
    expect(view).toContain("usedMarkers");
    expect(view).toContain("PlanificacionPoolCardsStrip");
  });
});
