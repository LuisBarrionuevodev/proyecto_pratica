import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import {
  buildDistritoMapLabels,
  resolveDistritoPolygonLabel,
} from "./planificacion/utils/planificacionMapaGeo";
import { reconcileSelectedIniciadorIds } from "./utils/poolAssignSync";

const read = (rel: string) => readFileSync(resolve(process.cwd(), rel), "utf8");

describe("RUTA-UX-CIERRE.1 — contexto Planificación al cambiar step", () => {
  const indexSrc = read("src/Containers/RutasTrabajo/index.tsx");
  const planificacionView = read("src/Containers/RutasTrabajo/planificacion/PlanificacionView.tsx");
  const controllerSrc = read("src/Containers/RutasTrabajo/planificacion/hooks/usePlanificacionController.ts");
  const mapaSrc = read("src/Containers/RutasTrabajo/planificacion/PlanificacionMapaDistritos.tsx");

  it("A — PlanificacionView permanece montada (display none, no unmount por step)", () => {
    expect(indexSrc).toContain('display: flowStep === 1 ? "flex" : "none"');
    expect(indexSrc).toContain("key={rutaId}");
    expect(indexSrc).not.toMatch(/\{flowStep === 1 &&[\s\S]*?<PlanificacionView/);
  });

  it("B — filtros tipo/rubro/q siguen client-side en controller", () => {
    expect(controllerSrc).toMatch(/filtrarPendientesMapaPorFiltros/);
    expect(controllerSrc).not.toMatch(/\[cardActiva,\s*filtros\.q,\s*filtros\.rubro_id,\s*loadPendientesMapa\]/);
  });

  it("C — conserva distrito/outside/tipo-rubro-q en controller (no reset por step)", () => {
    expect(controllerSrc).toContain("distritoActivoId");
    expect(controllerSrc).toContain("scopeOutsideDistricts");
    expect(controllerSrc).toContain("m4DistritoCacheRef");
    expect(controllerSrc).toContain("m4OutsideCacheRef");
    expect(planificacionView).toContain("usePlanificacionController");
  });

  it("D/E — M4 cache distrito/outside en controller", () => {
    expect(controllerSrc).toContain("m4OutsideCacheRef.current");
    expect(controllerSrc).toMatch(/cache\.get\(distritoActivoId\)/);
  });

  it("F — no nuevo M2 por cambio de step (M2 no depende de flowStep)", () => {
    expect(indexSrc).not.toMatch(/flowStep[\s\S]*loadCargaDistritos/);
    expect(controllerSrc).toContain("loadCargaDistritos({ silent: true })");
  });

  it("G — cambio de ruta remonta PlanificacionView con key rutaId", () => {
    expect(indexSrc).toContain("key={rutaId}");
  });

  it("Leaflet invalidateSize al volver visible", () => {
    expect(planificacionView).toContain("mapLayoutActive={visible}");
    expect(mapaSrc).toContain("PlanificacionMapInvalidateSize");
    expect(read("src/Containers/RutasTrabajo/planificacion/PlanificacionMapInvalidateSize.tsx")).toContain(
      "invalidateSize"
    );
  });
});

describe("RUTA-UX-CIERRE.1 — pool / M2 / M4 invalidación", () => {
  const controllerSrc = read("src/Containers/RutasTrabajo/planificacion/hooks/usePlanificacionController.ts");
  const cacheSrc = read("src/Containers/RutasTrabajo/planificacion/utils/m4DistritoCache.ts");

  it("A — pool mutation dispara refresh M2 silent", () => {
    expect(controllerSrc).toContain("poolM2RefreshSkipRef");
    expect(controllerSrc).toContain("loadCargaDistritos({ silent: true })");
  });

  it("B — M2 silent no activa loading cargaDistritos", () => {
    expect(controllerSrc).toMatch(/if \(!silent\) \{[\s\S]*cargaDistritos: true/);
    expect(controllerSrc).toMatch(/if \(!silent\) \{[\s\S]*cargaDistritos: false/);
  });

  it("C — invalidación M4 parcial con outside ref", () => {
    expect(controllerSrc).toContain("outsideCacheRef: m4OutsideCacheRef");
    expect(cacheSrc).toContain("applyM4InvalidationOnPoolRemoval");
    expect(cacheSrc).not.toMatch(/needsFullClear[\s\S]*cache\.clear\(\)/);
  });
});

describe("RUTA-UX-CIERRE.1 — selección Asignación", () => {
  const asignacionSrc = read("src/Containers/RutasTrabajo/views/RutasPlanificacionView.tsx");
  const indexSrc = read("src/Containers/RutasTrabajo/index.tsx");

  it("reconciliación selected ⊆ pool", () => {
    expect(asignacionSrc).toContain("reconcileSelectedIniciadorIds");
    expect(asignacionSrc).toContain("poolDisponibleIniciadorIds");
  });

  it("limpia selección al cambiar ruta", () => {
    expect(asignacionSrc).toMatch(/useEffect\(\(\) => \{[\s\S]*setSelectedIniciadorIds\(\[\]\)[\s\S]*\}, \[ruta\.id\]\)/);
  });

  it("defensa assign intersecta con pool antes de request", () => {
    expect(asignacionSrc).toContain("idsParaAsignar");
    expect(indexSrc).toContain("poolDisponibleIds");
    expect(indexSrc).toContain("iniciadorIdsEnPool.length === 0) return false");
  });

  it("reconcileSelectedIniciadorIds — elimina stale", () => {
    expect(reconcileSelectedIniciadorIds([1, 2, 3], [2, 4])).toEqual([2]);
    expect(reconcileSelectedIniciadorIds([1, 2], [1, 2])).toEqual([1, 2]);
    expect(reconcileSelectedIniciadorIds([], [1])).toEqual([]);
  });
});

describe("RUTA-UX-CIERRE.1 — outside UI top-right", () => {
  const mapaSrc = read("src/Containers/RutasTrabajo/planificacion/PlanificacionMapaDistritos.tsx");

  it("chip en overlay superior derecho", () => {
    expect(mapaSrc).toContain("planificacion-fuera-distritos-chip");
    expect(mapaSrc).toContain("top: 12");
    expect(mapaSrc).toContain("right: 12");
    expect(mapaSrc).not.toMatch(/bottom:\s*12[\s\S]*planificacion-fuera-distritos-chip/);
  });

  it("bottom-left sin chip outside (solo leyenda)", () => {
    const legendSrc = read("src/Containers/RutasTrabajo/planificacion/PlanificacionMapaLegend.tsx");
    expect(legendSrc).toContain("bottom");
    expect(legendSrc).not.toContain("Fuera de distritos");
  });
});

describe("RUTA-UX-CIERRE.1 — labels polígono código distrito", () => {
  it("label usa codigo, no cantidad", () => {
    expect(resolveDistritoPolygonLabel({ distrito_codigo: 10, cantidad: 250 })).toBe("10");
    expect(resolveDistritoPolygonLabel({ distrito_id: 3, cantidad: 99 })).toBe("3");
    expect(resolveDistritoPolygonLabel({ distrito_nombre: "Distrito 7", cantidad: 50 })).toBe("7");
  });

  it("buildDistritoMapLabels no usa cantidad como texto", () => {
    const labels = buildDistritoMapLabels({
      type: "FeatureCollection",
      features: [
        {
          type: "Feature",
          properties: { distrito_id: 10, distrito_codigo: 10, cantidad: 250 },
          geometry: {
            type: "Polygon",
            coordinates: [
              [
                [-65.22, -26.82],
                [-65.21, -26.82],
                [-65.21, -26.81],
                [-65.22, -26.81],
                [-65.22, -26.82],
              ],
            ],
          },
        },
      ],
    });
    expect(labels).toHaveLength(1);
    expect(labels[0].label).toBe("10");
    expect(labels[0].label).not.toBe("250");
  });

  it("merge agrega distrito_codigo desde catálogo", () => {
    const mergeSrc = read("src/Containers/RutasTrabajo/planificacion/utils/mergePlanificacionDistritosGeo.ts");
    expect(mergeSrc).toContain("distrito_codigo");
    expect(mergeSrc).toContain("cat.codigo");
  });

  it("label layer no interactivo", () => {
    const layerSrc = read("src/Containers/RutasTrabajo/planificacion/PlanificacionMapaDistritoLabelsLayer.tsx");
    expect(layerSrc).toContain("interactive={false}");
  });
});
