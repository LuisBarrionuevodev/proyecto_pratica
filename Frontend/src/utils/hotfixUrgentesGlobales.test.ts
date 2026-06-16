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
    expect(src).toContain('label="Global"');
    expect(src).toContain("Tooltip");
    expect(src).not.toContain("No cambia al seleccionar distrito.");
    expect(src).not.toContain("pendientes del contexto");
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

describe("FIX FINAL urgentes — layout y filtros", () => {
  it("Urgentes usa viewport con altura mínima definida", () => {
    const urgentes = read("src/Containers/RutasTrabajo/planificacion/UrgentesPanel.tsx");
    const styles = read("src/Containers/RutasTrabajo/styles/institutionalVisual.ts");
    expect(styles).toContain("planificacionUrgentesListViewportSx");
    expect(styles).toContain("16rem");
    expect(urgentes).toContain("planificacionUrgentesListViewportSx");
    expect(urgentes).toContain("planificacionFixedSectionSx");
  });

  it("slot Urgentes tiene minHeight para no colapsar con pool", () => {
    const styles = read("src/Containers/RutasTrabajo/styles/institutionalVisual.ts");
    expect(styles).toContain("planificacionUrgentesSlotSx");
    expect(styles).toMatch(/planificacionUrgentesSlotSx[\s\S]*minHeight/);
    expect(styles).toContain("planificacionPoolListViewportSx");
  });
});

describe("FIX UX urgentes compacto — vista principal", () => {
  it("UrgentesPanel muestra título Urgentes globales", () => {
    const src = read("src/Containers/RutasTrabajo/planificacion/UrgentesPanel.tsx");
    expect(src).toContain("Urgentes globales");
  });

  it("filtros compactos: tipo, domicilio, limpiar y buscar", () => {
    const src = read("src/Containers/RutasTrabajo/planificacion/UrgentesFiltroPanel.tsx");
    expect(src).toContain('label="Tipo urgente"');
    expect(src).toContain('label="Domicilio"');
    expect(src).toContain("Limpiar");
    expect(src).toContain("Buscar");
    expect(src).toContain("onClick={handleFiltrar}");
    expect(src).toContain('e.key === "Enter"');
  });

  it("no muestra textos explicativos largos ni filtros avanzados", () => {
    const panel = read("src/Containers/RutasTrabajo/planificacion/UrgentesPanel.tsx");
    const filtro = read("src/Containers/RutasTrabajo/planificacion/UrgentesFiltroPanel.tsx");
    expect(panel).not.toContain("pendientes del contexto");
    expect(filtro).not.toContain("Filtros sobre urgentes globales");
    expect(filtro).not.toContain("PlanificacionRubroSelect");
    expect(filtro).not.toContain("Nº oficio / comprobación / notificación");
    expect(filtro).not.toContain("setRubroId");
    expect(filtro).not.toContain("setQIdentificador");
  });

  it("filtros en fila compacta con flexShrink 0", () => {
    const filtro = read("src/Containers/RutasTrabajo/planificacion/UrgentesFiltroPanel.tsx");
    const styles = read("src/Containers/RutasTrabajo/styles/institutionalVisual.ts");
    expect(filtro).toContain("planificacionUrgentesFiltrosSx");
    expect(filtro).toContain('direction="row"');
    expect(styles).toContain("planificacionUrgentesFiltrosSx");
  });

  it("limpiar resetea domicilio y delega al controller", () => {
    const src = read("src/Containers/RutasTrabajo/planificacion/UrgentesFiltroPanel.tsx");
    expect(src).toContain("setQDomicilio");
    expect(src).toContain("onLimpiar()");
    expect(src).toContain("rubro_id: null");
    expect(src).toContain('q_identificador: ""');
  });
});
