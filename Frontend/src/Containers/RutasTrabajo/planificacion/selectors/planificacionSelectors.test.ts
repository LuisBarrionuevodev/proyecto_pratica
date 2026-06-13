import { describe, expect, it } from "vitest";

import { computeMetricasDesdeFilas } from "./planificacionSelectors";
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
    ...partial,
  };
}

describe("computeMetricasDesdeFilas", () => {
  it("cuenta solo filas del dataset visible", () => {
    const rows = [
      row({ id: 1, tipo_iniciador: "DENUNCIA", prioridad: 3 }),
      row({ id: 2, tipo_iniciador: "REINSPECCION_NOTIFICACION", prioridad: 3 }),
      row({ id: 3, tipo_iniciador: "RELEVAMIENTO", prioridad: 1 }),
      row({ id: 4, tipo_iniciador: "REINSPECCION_OFICIO", prioridad: 4 }),
    ];
    const m = computeMetricasDesdeFilas(rows);
    expect(m.total).toBe(4);
    expect(m.denuncias).toBe(1);
    expect(m.notificaciones).toBe(1);
    expect(m.relevamientos).toBe(1);
    expect(m.oficios_urgentes).toBe(1);
    expect(m.alta).toBe(3);
  });
});
