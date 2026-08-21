import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const read = (rel: string) => readFileSync(resolve(process.cwd(), rel), "utf8");

describe("OPER-RUTA.7C.2 — header compacto + espacio vertical", () => {
  it("RutaTrabajoCompactHeader integra stepper y acciones por slide (sin chips de ruta)", () => {
    const header = read("src/Containers/RutasTrabajo/Components/RutaTrabajoCompactHeader.tsx");
    expect(header).toContain("RutasTrabajoFlowStepper");
    const stepper = read("src/Containers/RutasTrabajo/Components/RutasTrabajoFlowStepper.tsx");
    expect(stepper).toContain("Planificación");
    expect(stepper).toContain("Asignación");
    expect(stepper).toContain("Mapa final");
    expect(header).toContain('data-testid="ruta-trabajo-compact-header"');
    expect(header).toContain("Elegir otra ruta");
    expect(header).toContain("Continuar a asignación");
    expect(header).toContain("Volver a planificación");
    expect(header).toContain("Continuar a mapa final");
    expect(header).toContain("Volver a asignación");
    expect(header).toContain('data-testid="header-publicar-ruta"');
    expect(header).not.toContain("turnoLabel");
    expect(header).not.toContain("estadoRutaVisible");
  });

  it("index usa header compacto en lugar de stepper + resumen separado", () => {
    const index = read("src/Containers/RutasTrabajo/index.tsx");
    expect(index).toContain("RutaTrabajoCompactHeader");
    expect(index).not.toContain("<RutasTrabajoFlowStepper");
    expect(index).not.toContain("RutaResumenHeaderCard");
  });

  it("Planificación no renderiza caja Resumen de ruta ni botón Continuar duplicado", () => {
    const view = read("src/Containers/RutasTrabajo/planificacion/PlanificacionView.tsx");
    expect(view).not.toContain("RutaResumenHeaderCard");
    expect(view).not.toContain("Resumen de ruta");
    expect(view).not.toContain("Continuar a asignación");
    expect(view).not.toContain("onVolverAElegirRuta");
    expect(view).toContain("PlanificacionSidebarPanel");
    const sidebar = read("src/Containers/RutasTrabajo/planificacion/PlanificacionSidebarPanel.tsx");
    expect(sidebar).toContain("Total mapa");
    expect(sidebar).toContain("Urgentes");
  });

  it("Asignación no renderiza caja Resumen de ruta y panel Grupos muestra resumen compacto", () => {
    const asignacion = read("src/Containers/RutasTrabajo/views/RutasPlanificacionView.tsx");
    expect(asignacion).not.toContain("RutaResumenHeaderCard");
    expect(asignacion).not.toContain("Resumen de ruta");
    expect(asignacion).not.toContain("AsignacionTopSection");
    expect(asignacion).toContain("AsignacionGruposResumenChips");
    expect(asignacion).toContain("+ Nuevo grupo");
    const panelGrupos = read("src/Containers/RutasTrabajo/Components/PanelGruposRuta.tsx");
    expect(panelGrupos).toContain("Gestionar items");
    expect(panelGrupos).toContain("Inspectores");
    expect(panelGrupos).toContain("Eliminar");
  });

  it("AsignacionGruposResumenChips expone métricas Grupos/Items/Inspectores/Observaciones", () => {
    const chips = read("src/Containers/RutasTrabajo/Components/AsignacionGruposResumenChips.tsx");
    expect(chips).toContain("Grupos:");
    expect(chips).toContain("Items:");
    expect(chips).toContain("Inspectores:");
    expect(chips).toContain("Observaciones:");
    expect(chips).toContain('data-testid="asignacion-grupos-resumen"');
  });

  it("Mapa final no renderiza Resumen de ruta; Publicar en header e indicadores con contexto", () => {
    const mapa = read("src/Containers/RutasTrabajo/views/RutasMapaOperativoView.tsx");
    expect(mapa).not.toContain("RutaResumenHeaderCard");
    expect(mapa).not.toContain("Resumen de ruta");
    expect(mapa).not.toContain('data-testid="mapa-final-publicar-action"');
    expect(mapa).toContain('data-testid="mapa-final-indicadores"');
    expect(mapa).toContain('data-testid="mapa-final-export-actions"');
    expect(mapa).toContain("Descargar resumen (PDF)");
    expect(mapa).not.toContain('<Alert');
    expect(mapa).toContain("RutaContextoLine");
    expect(mapa).toContain("useAppFeedback");
    const index = read("src/Containers/RutasTrabajo/index.tsx");
    expect(index).toContain("useAppFeedback");
    expect(index).not.toContain("<Snackbar");
  });

  it("Planificación gana alto tras eliminar resumen (layout 7C.2/7C.3)", () => {
    const layout = read("src/Containers/RutasTrabajo/planificacion/planificacionMyMapsLayout.ts");
    expect(layout).toContain("planificacionMainAreaSx");
    expect(layout).toContain("calc(100vh -");
  });
});
