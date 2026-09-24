import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const read = (rel: string) => readFileSync(resolve(process.cwd(), rel), "utf8");

describe("OPER-RUTA.FUNCIONAL-2A — pool/grupo siempre visibles en mapa", () => {
  it("builder ya no filtra por distritoActivoId", () => {
    const src = read("src/Containers/RutasTrabajo/planificacion/utils/buildPlanificacionUsedMarkers.ts");
    expect(src).not.toContain("matchesDistrito");
    expect(src).not.toContain("distritoActivoId");
  });

  it("PlanificacionView no pasa distritoActivoId al builder", () => {
    const view = read("src/Containers/RutasTrabajo/planificacion/PlanificacionView.tsx");
    expect(view).toContain("buildPlanificacionUsedMarkers");
    expect(view).not.toContain("distritoActivoId: ctrl.distritoActivoId");
  });

  it("caso 6: candidatos siguen condicionados por distrito activo", () => {
    const mapa = read("src/Containers/RutasTrabajo/planificacion/PlanificacionMapaDistritos.tsx");
    expect(mapa).toContain("PlanificacionMapaPendientesLayer");
    expect(mapa).toMatch(/PlanificacionMapaPendientesLayer[\s\S]*visible=\{distritoActivoId != null\}/);
  });

  it("capa usada ya no depende de distritoActivoId", () => {
    const mapa = read("src/Containers/RutasTrabajo/planificacion/PlanificacionMapaDistritos.tsx");
    expect(mapa).toContain("<PlanificacionMapaUsedLayer markers={usedMarkers} />");
    expect(mapa).not.toMatch(/<PlanificacionMapaUsedLayer[^>]*visible=/);
  });

  it("PlanificacionMapaUsedLayer no expone prop visible", () => {
    const layer = read("src/Containers/RutasTrabajo/planificacion/PlanificacionMapaUsedLayer.tsx");
    expect(layer).not.toContain("visible?:");
    expect(layer).not.toContain("if (!visible)");
  });
});
