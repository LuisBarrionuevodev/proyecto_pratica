import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const read = (rel: string) => readFileSync(resolve(process.cwd(), rel), "utf8");

describe("STAB-10c-REWORK KPIs restaurados", () => {
  it("renderiza múltiples KPIs clicables", () => {
    const src = read("src/Containers/RutasTrabajo/planificacion/PlanificacionSummaryCards.tsx");
    expect(src).toContain("OFICIOS_URGENTES");
    expect(src).toContain("DENUNCIAS");
    expect(src).toContain("NOTIFICACIONES");
    expect(src).toContain("onCardChange");
    expect(src).not.toContain("Indicador único");
  });

  it("PlanificacionView restaura cardActiva y onCardChange", () => {
    const src = read("src/Containers/RutasTrabajo/planificacion/PlanificacionView.tsx");
    expect(src).toContain("cardActiva={ctrl.cardActiva}");
    expect(src).toContain("onCardChange={ctrl.setCardActiva}");
  });

  it("controller usa dataset mapa para KPIs y filtro por card", () => {
    const src = read(
      "src/Containers/RutasTrabajo/planificacion/hooks/usePlanificacionController.ts"
    );
    expect(src).toContain("computeMetricasCardsDesdeMapa(pendientesMapaBase)");
    expect(src).toContain("filtrarPendientesMapaPorCard(pendientesMapaBase, cardActiva)");
    expect(src).toContain("filasConPinMapa");
    expect(src).not.toContain("buildM4QueryBase(distritoActivoId, cardActiva");
  });

  it("leyenda indica indicadores sobre mapa visible", () => {
    const src = read("src/Containers/RutasTrabajo/planificacion/PlanificacionSummaryCards.tsx");
    expect(src).toContain("Indicadores calculados sobre direcciones visibles en mapa");
  });
});

describe("STAB-10c-REWORK identificadores se mantienen", () => {
  it("cards compactas siguen con identificadores", () => {
    const src = read(
      "src/Containers/RutasTrabajo/planificacion/components/PlanificacionIniciadorCompactCard.tsx"
    );
    expect(src).toContain("lineasIdentificadoresPendiente");
  });
});
