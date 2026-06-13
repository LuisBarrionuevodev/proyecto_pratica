import { describe, expect, it } from "vitest";

import {
  computeMetricasCardsDesdeMapa,
  filasConPinMapa,
  filtrarPendientesMapaPorCard,
} from "./planificacionSelectors";
import type { IPlanificacionPendiente } from "../types/planificacion.types";

function row(partial: Partial<IPlanificacionPendiente> & { id: number }): IPlanificacionPendiente {
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
    lat: partial.lat ?? -34.6,
    lng: partial.lng ?? -58.4,
    ...partial,
  };
}

describe("computeMetricasCardsDesdeMapa", () => {
  it("cuenta solo filas del dataset mapa", () => {
    const rows = [
      row({ id: 1, tipo_iniciador: "DENUNCIA", prioridad: 3 }),
      row({ id: 2, tipo_iniciador: "REINSPECCION_NOTIFICACION", prioridad: 3 }),
      row({ id: 3, tipo_iniciador: "RELEVAMIENTO", prioridad: 1 }),
      row({ id: 4, tipo_iniciador: "REINSPECCION_OFICIO", prioridad: 4 }),
    ];
    const m = computeMetricasCardsDesdeMapa(rows);
    expect(m.total).toBe(4);
    expect(m.denuncias).toBe(1);
    expect(m.notificaciones).toBe(1);
    expect(m.relevamientos).toBe(1);
    expect(m.oficios_urgentes).toBe(1);
    expect(m.alta).toBe(3);
  });
});

describe("filasConPinMapa", () => {
  it("excluye filas sin coordenadas", () => {
    const rows = [
      row({ id: 1 }),
      row({ id: 2, lat: null, lng: null }),
    ];
    expect(filasConPinMapa(rows)).toHaveLength(1);
    expect(filasConPinMapa(rows)[0].id).toBe(1);
  });
});

describe("filtrarPendientesMapaPorCard", () => {
  const dataset = [
    row({ id: 1, tipo_iniciador: "DENUNCIA" }),
    row({ id: 2, tipo_iniciador: "REINSPECCION_OFICIO" }),
    row({ id: 3, tipo_iniciador: "REINSPECCION_NOTIFICACION" }),
    row({ id: 4, tipo_iniciador: "RELEVAMIENTO", prioridad: 1 }),
    row({ id: 5, tipo_iniciador: "DENUNCIA", prioridad: 4 }),
  ];

  it("Oficios devuelve solo tipos oficio del mapa", () => {
    const out = filtrarPendientesMapaPorCard(dataset, "OFICIOS_URGENTES");
    expect(out.map((r) => r.id)).toEqual([2]);
  });

  it("Denuncias devuelve solo denuncias del mapa", () => {
    const out = filtrarPendientesMapaPorCard(dataset, "DENUNCIAS");
    expect(out.map((r) => r.id)).toEqual([1, 5]);
  });

  it("Notificaciones devuelve solo reinspección notificación", () => {
    const out = filtrarPendientesMapaPorCard(dataset, "NOTIFICACIONES");
    expect(out.map((r) => r.id)).toEqual([3]);
  });

  it("Alta excluye relevamiento y prioridad baja", () => {
    const out = filtrarPendientesMapaPorCard(dataset, "ALTA_PRIORIDAD");
    expect(out.map((r) => r.id)).toEqual([1, 2, 3, 5]);
  });
});
