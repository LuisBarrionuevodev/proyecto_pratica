import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const read = (rel: string) => readFileSync(resolve(process.cwd(), rel), "utf8");

describe("V1.1-RESP.3-C — ruta abierta y planificación mobile-first", () => {
  it("stepper vertical en xs y horizontal desde sm", () => {
    const stepper = read("src/Containers/RutasTrabajo/Components/RutasTrabajoFlowStepper.tsx");
    expect(stepper).toContain('direction={{ xs: "column", sm: "row" }}');
    expect(stepper).toContain('width: { xs: 1, sm: 16 }');
    expect(stepper).toContain('height: { xs: 10, sm: 1 }');
  });

  it("header compacto alinea stepper y acciones desde sm", () => {
    const header = read("src/Containers/RutasTrabajo/Components/RutaTrabajoCompactHeader.tsx");
    expect(header).toContain('direction={{ xs: "column", sm: "row" }}');
    expect(header).toContain("minWidth: 0");
  });

  it("planificación apila sidebar y mapa hasta md", () => {
    const view = read("src/Containers/RutasTrabajo/planificacion/PlanificacionView.tsx");
    expect(view).toContain('size={{ xs: 12, md: 4 }}');
    expect(view).toContain('size={{ xs: 12, md: 8 }}');
    const layout = read("src/Containers/RutasTrabajo/planificacion/planificacionMyMapsLayout.ts");
    expect(layout).toContain("PLANIFICACION_MAP_VIEWPORT_HEIGHT_XS");
    expect(layout).toContain('xs: "auto"');
    expect(layout).toContain("calc(100vh -");
  });

  it("shell de ruta abierta evita overflow horizontal global", () => {
    const index = read("src/Containers/RutasTrabajo/index.tsx");
    expect(index).toContain('overflowX: rutaId != null ? "hidden"');
  });

  it("mapa de planificación usa altura contenida en viewport angosto", () => {
    const mapa = read("src/Containers/RutasTrabajo/planificacion/PlanificacionMapaDistritos.tsx");
    expect(mapa).toContain("PLANIFICACION_MAP_VIEWPORT_HEIGHT_XS");
    expect(mapa).toContain('maxWidth: "100%"');
  });
});
