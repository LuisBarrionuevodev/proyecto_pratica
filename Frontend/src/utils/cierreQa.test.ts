import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { buildUrgentesQueryParams } from "../Containers/RutasTrabajo/planificacion/utils/buildUrgentesQueryParams";
import {
  filtrarPendientesMapaPorCard,
  filtrarUrgentesVisibles,
} from "../Containers/RutasTrabajo/planificacion/selectors/planificacionSelectors";
import type { IPlanificacionPendiente } from "../Containers/RutasTrabajo/planificacion/types/planificacion.types";

const read = (rel: string) => readFileSync(resolve(process.cwd(), rel), "utf8");

function urgenteRow(partial: Partial<IPlanificacionPendiente> & { id: number }): IPlanificacionPendiente {
  return {
    id: partial.id,
    tipo_iniciador: partial.tipo_iniciador ?? "DENUNCIA",
    estado_iniciador: "PENDIENTE",
    fecha_origen: null,
    prioridad: partial.prioridad ?? 3,
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
    elegible_urgente: partial.elegible_urgente,
    ...partial,
  };
}

describe("CIERRE-QA H — Urgentes visibles", () => {
  it("M3 con items → filtrarUrgentesVisibles conserva filas fuera del pool", () => {
    const rows = [urgenteRow({ id: 1 }), urgenteRow({ id: 2 })];
    const pool = new Set([2]);
    expect(filtrarUrgentesVisibles(rows, pool).map((r) => r.id)).toEqual([1]);
  });

  it("M3 vacío → sin filas visibles", () => {
    expect(filtrarUrgentesVisibles([], new Set())).toEqual([]);
  });

  it("filtros vacíos no envían parámetros que oculten resultados", () => {
    const q = buildUrgentesQueryParams({
      page: 1,
      per_page: 25,
      filtros: { tipo_urgente: "", rubro_id: null, q_identificador: "", q_domicilio: "" },
    });
    expect(q).toEqual({ page: 1, per_page: 25 });
  });

  it("limpiar filtros usa URGENTES_FILTROS_VACIOS en controller", () => {
    const src = read("src/Containers/RutasTrabajo/planificacion/hooks/usePlanificacionController.ts");
    expect(src).toContain("URGENTES_FILTROS_VACIOS");
    expect(src).toContain("limpiarFiltrosUrgentes");
    expect(src).toContain("filtrarUrgentesVisibles");
    expect(src).not.toContain("elegible_urgente === false");
  });

  it("cardActiva no afecta urgentes (solo pendientes mapa)", () => {
    const dataset = [
      urgenteRow({ id: 1, tipo_iniciador: "DENUNCIA" }),
      urgenteRow({ id: 2, tipo_iniciador: "RELEVAMIENTO", prioridad: 1 }),
    ];
    const urgentes = filtrarUrgentesVisibles(dataset, new Set());
    const porCard = filtrarPendientesMapaPorCard(dataset, "DENUNCIAS");
    expect(urgentes).toHaveLength(2);
    expect(porCard).toHaveLength(1);
  });

  it("UrgentesPanel tiene viewport de lista con scroll propio", () => {
    const src = read("src/Containers/RutasTrabajo/planificacion/UrgentesPanel.tsx");
    expect(src).toContain("planificacionListViewportSx");
    expect(src).toContain("PlanificacionIniciadorCompactCard");
  });

  it("empty state distingue sin urgentes vs sin página", () => {
    const src = read("src/Containers/RutasTrabajo/planificacion/UrgentesPanel.tsx");
    expect(src).toContain('meta.total === 0');
    expect(src).toContain("Sin urgentes");
  });
});

describe("CIERRE-QA I — Modal asignar inspectores scroll único", () => {
  it("DialogContent usa flex sin overflow externo", () => {
    const modal = read("src/Containers/RutasTrabajo/Components/ModalAsignarInspectoresGrupo.tsx");
    const styles = read("src/styles/formDialogStyles.ts");
    expect(modal).toContain("formDialogFlexScrollBodySx");
    expect(styles).toContain("overflow: \"hidden\"");
    expect(modal).toContain('overflow: "auto"');
  });

  it("lista es el único contenedor con overflow auto en el modal", () => {
    const modal = read("src/Containers/RutasTrabajo/Components/ModalAsignarInspectoresGrupo.tsx");
    const autoCount = (modal.match(/overflow:\s*"auto"/g) ?? []).length;
    expect(autoCount).toBe(1);
  });

  it("botón Listo queda fuera del viewport scrolleable", () => {
    const modal = read("src/Containers/RutasTrabajo/Components/ModalAsignarInspectoresGrupo.tsx");
    const listIdx = modal.indexOf("ref={listParentRef}");
    const listoIdx = modal.indexOf("Listo");
    expect(listIdx).toBeGreaterThan(-1);
    expect(listoIdx).toBeGreaterThan(listIdx);
  });
});
