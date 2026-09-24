import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { buildPlanificacionUsedMarkers } from "./planificacion/utils/buildPlanificacionUsedMarkers";
import { sinPool } from "./planificacion/selectors/planificacionSelectors";

const root = resolve(__dirname, "../..");

function read(rel: string): string {
  return readFileSync(resolve(root, rel), "utf8");
}

describe("OPER-RUTA.7C.1 — panel planificación My Maps", () => {
  const sidebar = read("Containers/RutasTrabajo/planificacion/PlanificacionSidebarPanel.tsx");
  const filtros = read("Containers/RutasTrabajo/planificacion/PlanificacionFiltrosBar.tsx");
  const chips = read("Containers/RutasTrabajo/planificacion/components/PlanificacionTipoFilterChips.tsx");
  const view = read("Containers/RutasTrabajo/planificacion/PlanificacionView.tsx");
  const mapa = read("Containers/RutasTrabajo/planificacion/PlanificacionMapaDistritos.tsx");
  const controller = read("Containers/RutasTrabajo/planificacion/hooks/usePlanificacionController.ts");

  it("renderiza tabs Total mapa y Urgentes", () => {
    expect(sidebar).toContain('"total-mapa"');
    expect(sidebar).toContain("Total mapa");
    expect(sidebar).toContain("Urgentes");
    expect(sidebar).toContain("planificacion-tab-");
  });

  it("no renderiza tabs Candidatos, Pool ni Resumen", () => {
    expect(sidebar).not.toContain('"candidatos"');
    expect(sidebar).not.toContain("PoolDelDiaPanel");
    expect(sidebar).not.toContain("PlanificacionResumenPanel");
    expect(sidebar).not.toMatch(/label:\s*"Pool"/);
    expect(sidebar).not.toMatch(/label:\s*"Resumen"/);
  });

  it("no renderiza botón Continuar a asignación dentro del panel lateral", () => {
    expect(sidebar).not.toContain("planificacion-continuar-asignacion");
    expect(sidebar).not.toContain("Continuar a asignación");
    expect(view).not.toContain("Continuar a asignación");
    const header = read("Containers/RutasTrabajo/Components/RutaTrabajoCompactHeader.tsx");
    expect(header).toContain("Continuar a asignación");
  });

  it("Total mapa muestra chips Todos/Relev./Notif./Oficios/Denuncias sin Alta", () => {
    expect(chips).toContain('variant?: "totalMapa"');
    expect(chips).toContain('"RELEVAMIENTOS"');
    expect(chips).toContain('"NOTIFICACIONES"');
    expect(chips).toContain('"OFICIOS_URGENTES"');
    expect(chips).toContain('"DENUNCIAS"');
    expect(chips).not.toContain('"ALTA_PRIORIDAD"');
  });

  it("Urgentes muestra chips Todos/Notif./Oficios/Denuncias", () => {
    expect(chips).toContain("CHIPS_URGENTES");
    expect(chips).toContain('"NOTIFICACION"');
    expect(chips).toContain('"OFICIO"');
    expect(chips).toContain('"DENUNCIA"');
    expect(chips).not.toMatch(/CHIPS_URGENTES:[\s\S]*RELEVAMIENTOS/);
  });

  it("no repite distrito en chips activos redundantes dentro del panel", () => {
    expect(filtros).not.toContain("PlanificacionActiveFiltersChips");
    expect(filtros).not.toContain("MapOutlinedIcon");
    expect(filtros).not.toMatch(/Distrito:\s/);
  });

  it("tabla/listado mantiene paginación visible", () => {
    expect(sidebar).toContain('variant="embedded"');
    expect(read("Containers/RutasTrabajo/planificacion/PendientesContextoPanel.tsx")).toContain(
      'className="planificacion-pagination-footer"'
    );
    expect(read("Containers/RutasTrabajo/planificacion/UrgentesPanel.tsx")).toContain(
      'className="planificacion-pagination-footer"'
    );
  });

  it("mapa incluye capa de pines usados y leyenda", () => {
    expect(view).toContain("buildPlanificacionUsedMarkers");
    expect(view).toContain("usedMarkers");
    expect(mapa).toContain("PlanificacionMapaUsedLayer");
    expect(mapa).toContain("PlanificacionMapaLegend");
    expect(read("Containers/RutasTrabajo/planificacion/PlanificacionMapaLegend.tsx")).toContain(
      "planificacion-mapa-legend"
    );
  });

  it("agregar al pool oculta candidato localmente sin refetch M4/M3", () => {
    expect(controller).toContain("sinPool(pendientesMapaRaw, poolSet)");
    expect(controller).not.toContain("poolIniciadorKey");
    const libres = sinPool([{ id: 1 }, { id: 2 }], new Set([2]));
    expect(libres.map((r) => r.id)).toEqual([1]);
  });
});

describe("OPER-RUTA.7C.1 — buildPlanificacionUsedMarkers", () => {
  it("pool row con coordenadas renderiza pin usado", () => {
    const markers = buildPlanificacionUsedMarkers({
      poolItems: [
        {
          pool_id: 1,
          fecha: "2026-05-19",
          estado: "EN_POOL",
          iniciador_id: 7,
          iniciador_ruta_id: 7,
          lat: -26.82,
          lng: -65.22,
        } as never,
      ],
      grupos: [],
      itemsActivos: [],
    });
    expect(markers).toHaveLength(1);
    expect(markers[0].estado).toBe("pool");
  });

  it("mismo iniciador en pool y grupo produce un solo pin con prioridad grupo", () => {
    const markers = buildPlanificacionUsedMarkers({
      poolItems: [
        {
          pool_id: 1,
          fecha: "2026-05-19",
          estado: "EN_POOL",
          iniciador_id: 7,
          iniciador_ruta_id: 7,
          lat: -26.82,
          lng: -65.22,
        } as never,
      ],
      grupos: [
        {
          id: 3,
          ruta_trabajo_id: 1,
          nombre: "Grupo X",
          estado: null,
          inspectores: [],
          created_by_user_id: 1,
          created_at: null,
          updated_at: null,
        },
      ],
      itemsActivos: [
        {
          id: 10,
          ruta_trabajo_id: 1,
          ruta_grupo_id: 3,
          iniciador_ruta_id: 7,
          estado_ruta_item: "PENDIENTE",
          deleted_at: null,
          lat: -26.83,
          lng: -65.23,
        } as never,
      ],
    });
    expect(markers).toHaveLength(1);
    expect(markers[0].estado).toBe("grupo");
    expect(markers[0].grupoNombre).toBe("Grupo X");
  });
});
