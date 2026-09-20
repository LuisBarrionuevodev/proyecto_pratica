import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const read = (rel: string) => readFileSync(resolve(process.cwd(), rel), "utf8");

describe("REL-MAP-CIERRE.5-6 Fuera de distritos", () => {
  it("renderiza chip Fuera de distritos (N) en overlay superior derecho", () => {
    const mapa = read("src/Containers/RutasTrabajo/planificacion/PlanificacionMapaDistritos.tsx");
    expect(mapa).toContain("Fuera de distritos (");
    expect(mapa).toContain("planificacion-fuera-distritos-chip");
    expect(mapa).toContain("top: 12");
    expect(mapa).toContain("right: 12");
    expect(mapa).not.toMatch(/bottom:\s*12[\s\S]*planificacion-fuera-distritos-chip/);
  });

  it("click chip llama onSelectOutsideDistricts", () => {
    const mapa = read("src/Containers/RutasTrabajo/planificacion/PlanificacionMapaDistritos.tsx");
    expect(mapa).toContain("onSelectOutsideDistricts");
    expect(mapa).toContain("onClick={onSelectOutsideDistricts}");
  });

  it("hook envía scope=outside_districts sin distrito_id", () => {
    const hook = read("src/Containers/RutasTrabajo/planificacion/hooks/usePlanificacionController.ts");
    expect(hook).toContain('scope: "outside_districts"');
    expect(hook).toContain("seleccionarFueraDeDistritos");
    expect(hook).toContain("setScopeOutsideDistricts(false)");
    expect(hook).not.toMatch(/distrito_id:.*scope:\s*"outside_districts"/);
  });

  it("seleccionar distrito desactiva scope outside", () => {
    const hook = read("src/Containers/RutasTrabajo/planificacion/hooks/usePlanificacionController.ts");
    const block = hook.slice(hook.indexOf("const seleccionarDistrito"), hook.indexOf("const seleccionarFueraDeDistritos") + 120);
    expect(block).toContain("setScopeOutsideDistricts(false)");
  });

  it("seleccionar outside limpia distritoActivoId", () => {
    const hook = read("src/Containers/RutasTrabajo/planificacion/hooks/usePlanificacionController.ts");
    const block = hook.slice(hook.indexOf("const seleccionarFueraDeDistritos"));
    expect(block).toContain("setDistritoActivoId(null)");
    expect(block).toContain("setScopeOutsideDistricts(true)");
  });

  it("API M2 expone outside_districts_count", () => {
    const api = read("src/Containers/RutasTrabajo/planificacion/api/planificacionApi.ts");
    expect(api).toContain("ICargaDistritosResponse");
    const types = read("src/Containers/RutasTrabajo/planificacion/types/planificacion.types.ts");
    expect(types).toContain("outside_districts_count");
  });

  it("pins visibles con scope outside", () => {
    const mapa = read("src/Containers/RutasTrabajo/planificacion/PlanificacionMapaDistritos.tsx");
    expect(mapa).toContain("scopeOutsideDistricts");
    expect(mapa).toMatch(/visible=\{distritoActivoId != null \|\| scopeOutsideDistricts\}/);
  });

  it("pool usa flujo existente agregarAlPool", () => {
    const view = read("src/Containers/RutasTrabajo/planificacion/PlanificacionView.tsx");
    expect(view).toContain("onAgregarCandidato={ctrl.agregarAlPool}");
    expect(view).toContain("onAgregarDesdeMapa={handleAgregarDesdeMapa}");
  });
});
