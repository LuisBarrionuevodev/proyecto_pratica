import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { buildUrgentesQueryParams } from "../Containers/RutasTrabajo/planificacion/utils/buildUrgentesQueryParams";
import {
  aplicarFiltrosPendientesContexto,
} from "../Containers/RutasTrabajo/planificacion/selectors/planificacionSelectors";
import type { IPlanificacionPendiente, PlanificacionFiltrosLista } from "../Containers/RutasTrabajo/planificacion/types/planificacion.types";

const read = (rel: string) => readFileSync(resolve(process.cwd(), rel), "utf8");

describe("STAB-10d buildUrgentesQueryParams", () => {
  it("envía q_identificador, q_domicilio y rubro_id sin vacíos", () => {
    const q = buildUrgentesQueryParams({
      filtros: {
        tipo_urgente: "OFICIO",
        rubro_id: 5,
        q_identificador: " 123 ",
        q_domicilio: "san martin",
      },
    });
    expect(q.tipo_urgente).toBe("OFICIO");
    expect(q.rubro_id).toBe(5);
    expect(q.q_identificador).toBe("123");
    expect(q.q_domicilio).toBe("san martin");
    expect(q).not.toHaveProperty("q");
    expect(q).not.toHaveProperty("numero_oficio");
  });

  it("tipo Todos y campos vacíos no envían filtros", () => {
    const q = buildUrgentesQueryParams({
      filtros: {
        tipo_urgente: "",
        rubro_id: null,
        q_identificador: "",
        q_domicilio: "",
      },
    });
    expect(Object.keys(q)).toEqual(["page", "per_page"]);
  });
});

describe("STAB-10d aplicarFiltrosPendientesContexto (frontend)", () => {
  const rows: IPlanificacionPendiente[] = [
    {
      id: 1,
      tipo_iniciador: "DENUNCIA",
      estado_iniciador: "PENDIENTE",
      fecha_origen: null,
      prioridad: 3,
      turno_sugerido: null,
      rubro_nombre: "Panadería",
      domicilio_texto: "Mitre 100",
      domicilio: { id: 1, calle: "Mitre", numero: "100", distrito_id: 1, barrio_id: null, rubro: "Panadería" },
      origen: {
        tipo: null,
        denuncia_id: null,
        relevamiento_id: null,
        notificacion_id: null,
        oficio_id: null,
        actuacion_id: null,
      },
      observaciones: null,
      lat: -34.6,
      lng: -58.4,
    },
    {
      id: 2,
      tipo_iniciador: "DENUNCIA",
      estado_iniciador: "PENDIENTE",
      fecha_origen: null,
      prioridad: 3,
      turno_sugerido: null,
      rubro_nombre: "Carnicería",
      domicilio_texto: "Rivadavia 200",
      domicilio: { id: 2, calle: "Rivadavia", numero: "200", distrito_id: 1, barrio_id: null, rubro: "Carnicería" },
      origen: {
        tipo: null,
        denuncia_id: null,
        relevamiento_id: null,
        notificacion_id: null,
        oficio_id: null,
        actuacion_id: null,
      },
      observaciones: null,
      lat: -34.61,
      lng: -58.41,
    },
  ];

  const rubroNombrePorId = (id: number) => (id === 10 ? "Panadería" : null);

  it("filtra por rubro_id vía nombre catálogo", () => {
    const filtros: PlanificacionFiltrosLista = { q: "", rubro_id: 10 };
    const out = aplicarFiltrosPendientesContexto(rows, filtros, rubroNombrePorId);
    expect(out.map((r) => r.id)).toEqual([1]);
  });

  it("filtra por domicilio q", () => {
    const filtros: PlanificacionFiltrosLista = { q: "rivadavia", rubro_id: null };
    const out = aplicarFiltrosPendientesContexto(rows, filtros, rubroNombrePorId);
    expect(out.map((r) => r.id)).toEqual([2]);
  });
});

describe("STAB-10d PendientesContextoPanel", () => {
  it("no muestra filtro por tipo ni ordenar general", () => {
    const panel = read("src/Containers/RutasTrabajo/planificacion/PendientesContextoPanel.tsx");
    const filtro = read("src/Containers/RutasTrabajo/planificacion/PendientesContextoFiltroPanel.tsx");
    expect(panel).not.toContain("Tipo de iniciador");
    expect(panel).not.toContain("Ordenar por");
    expect(filtro).not.toContain("TIPO_OPCIONES");
    expect(filtro).not.toContain("Ordenar por rubro");
  });

  it("muestra rubro catálogo y domicilio", () => {
    const src = read("src/Containers/RutasTrabajo/planificacion/PendientesContextoFiltroPanel.tsx");
    const rubro = read("src/Containers/RutasTrabajo/planificacion/components/PlanificacionRubroSelect.tsx");
    expect(src).toContain("PlanificacionRubroSelect");
    expect(src).toContain('label="Domicilio"');
    expect(rubro).toContain("fetchRubrosCatalogoCached");
  });

  it("usa estilos compactos iguales a Urgentes", () => {
    const src = read("src/Containers/RutasTrabajo/planificacion/PendientesContextoFiltroPanel.tsx");
    expect(src).toContain("filterCompactPrimaryButtonSx");
    expect(src).toContain("filterCompactSecondaryButtonSx");
    expect(src).toContain("filterCompactActionsSx");
  });
});

describe("STAB-10d UrgentesFiltroPanel", () => {
  it("muestra input identificador único y domicilio", () => {
    const src = read("src/Containers/RutasTrabajo/planificacion/UrgentesFiltroPanel.tsx");
    expect(src).toContain("Nº oficio / comprobación / notificación");
    expect(src).toContain('label="Domicilio"');
    expect(src).toContain("PlanificacionRubroSelect");
    expect(src).not.toContain('label="Nº oficio"');
    expect(src).not.toContain('label="Nº comprobación"');
  });

  it("busca solo por botón o Enter", () => {
    const src = read("src/Containers/RutasTrabajo/planificacion/UrgentesFiltroPanel.tsx");
    expect(src).toContain("onClick={handleFiltrar}");
    expect(src).not.toContain("useDebouncedValue");
  });

  it("limpiar resetea rubro e identificador", () => {
    const src = read("src/Containers/RutasTrabajo/planificacion/UrgentesFiltroPanel.tsx");
    expect(src).toContain("setRubroId(null)");
    expect(src).toContain("setQIdentificador");
    expect(src).toContain("setQDomicilio");
  });
});

describe("STAB-10d controller M4 sin filtros panel en API", () => {
  it("buildM4QueryBase solo distrito y orden prioridad", () => {
    const src = read("src/Containers/RutasTrabajo/planificacion/hooks/usePlanificacionController.ts");
    expect(src).toContain("aplicarFiltrosPendientesContexto");
    expect(src).not.toContain("filtros.tipo");
    expect(src).not.toContain("prioridad_categoria");
    const m4Effect = src.slice(src.indexOf("M4 mapa: solo distrito"));
    expect(m4Effect).not.toContain("filtros.q");
  });
});
