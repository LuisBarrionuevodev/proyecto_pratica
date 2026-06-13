import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { buildUrgentesQueryParams } from "../Containers/RutasTrabajo/planificacion/utils/buildUrgentesQueryParams";
import { filtrarPendientesMapaPorCard, filtrarUrgentesVisibles } from "../Containers/RutasTrabajo/planificacion/selectors/planificacionSelectors";
import type { IPlanificacionPendiente } from "../Containers/RutasTrabajo/planificacion/types/planificacion.types";

const read = (rel: string) => readFileSync(resolve(process.cwd(), rel), "utf8");

function row(id: number): IPlanificacionPendiente {
  return {
    id,
    tipo_iniciador: "DENUNCIA",
    estado_iniciador: "PENDIENTE",
    fecha_origen: null,
    prioridad: 3,
    turno_sugerido: null,
    domicilio: { id: 1, calle: null, numero: null, distrito_id: 1, barrio_id: null },
    origen: {
      tipo: null,
      denuncia_id: null,
      relevamiento_id: null,
      notificacion_id: null,
      oficio_id: null,
      actuacion_id: null,
    },
    observaciones: null,
  };
}

describe("HOTFIX urgentes globales — sin distrito del mapa", () => {
  it("loadUrgentes no pasa distrito_id al API", () => {
    const src = read("src/Containers/RutasTrabajo/planificacion/hooks/usePlanificacionController.ts");
    const loadBlock = src.slice(src.indexOf("const loadUrgentes"));
    const apiCall = loadBlock.slice(
      loadBlock.indexOf("getPlanificacionUrgentes"),
      loadBlock.indexOf("});", loadBlock.indexOf("getPlanificacionUrgentes")) + 3
    );
    expect(apiCall).not.toContain("distrito_id");
    expect(apiCall).toContain("filtros: f");
  });

  it("buildUrgentesQueryParams sin distrito no envía distrito_id", () => {
    expect(buildUrgentesQueryParams({ page: 1, per_page: 25 })).toEqual({
      page: 1,
      per_page: 25,
    });
  });

  it("filtros propios de Urgentes sí se envían", () => {
    const q = buildUrgentesQueryParams({
      page: 1,
      per_page: 25,
      filtros: {
        tipo_urgente: "DENUNCIA",
        rubro_id: 2,
        q_identificador: "99",
        q_domicilio: "mitre",
      },
    });
    expect(q.tipo_urgente).toBe("DENUNCIA");
    expect(q.rubro_id).toBe(2);
    expect(q.q_identificador).toBe("99");
    expect(q.q_domicilio).toBe("mitre");
    expect(q).not.toHaveProperty("distrito_id");
  });

  it("UrgentesPanel no muestra acotado al distrito", () => {
    const src = read("src/Containers/RutasTrabajo/planificacion/UrgentesPanel.tsx");
    expect(src).toContain("Urgentes globales");
    expect(src).not.toContain("Acotado al distrito");
    expect(src).not.toContain("distritoActivoNombre");
  });

  it("PlanificacionView no pasa distrito a UrgentesPanel", () => {
    const src = read("src/Containers/RutasTrabajo/planificacion/PlanificacionView.tsx");
    const block = src.slice(src.indexOf("<UrgentesPanel"), src.indexOf("<PoolDelDiaPanel"));
    expect(block).not.toContain("distritoActivoNombre");
  });

  it("cardActiva no filtra urgentes (solo pendientes mapa)", () => {
    const dataset = [row(1), row(2)];
    const urgentes = filtrarUrgentesVisibles(dataset, new Set());
    const porCard = filtrarPendientesMapaPorCard(dataset, "DENUNCIAS");
    expect(urgentes).toHaveLength(2);
    expect(porCard).toHaveLength(2);
  });

  it("pool oculta solo ítems agregados, no toda la bandeja", () => {
    const dataset = [row(1), row(2), row(3)];
    const visibles = filtrarUrgentesVisibles(dataset, new Set([2]));
    expect(visibles.map((r) => r.id)).toEqual([1, 3]);
  });
});
