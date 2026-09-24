import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import {
  formatoNumeroConAnio,
  lineasIdentificadoresPendiente,
} from "../Containers/RutasTrabajo/planificacion/utils/iniciadorDisplay";
import type { IRutaIniciadorPendienteRow } from "../api/rutasTrabajoApi";

const read = (rel: string) => readFileSync(resolve(process.cwd(), rel), "utf8");

describe("STAB-10c identificadores en cards", () => {
  const baseRow = {
    id: 1,
    tipo_iniciador: "REINSPECCION_OFICIO",
    estado_iniciador: "PENDIENTE",
    fecha_origen: "2026-06-01",
    prioridad: 3,
    turno_sugerido: null,
    domicilio: {
      id: 1,
      calle: "San Martín",
      numero: "100",
      distrito_id: 1,
      barrio_id: null,
    },
    origen: {
      tipo: "OFICIO",
      denuncia_id: null,
      relevamiento_id: null,
      notificacion_id: null,
      oficio_id: 1,
      actuacion_id: null,
    },
    observaciones: null,
  } satisfies IRutaIniciadorPendienteRow;

  it("card helper muestra Nº oficio y comprobación", () => {
    const lines = lineasIdentificadoresPendiente({
      ...baseRow,
      identificadores: {
        numero_oficio: "123",
        anio_oficio: 2026,
        numero_comprobacion: "456",
        anio_comprobacion: 2026,
      },
    });
    expect(lines).toContain("Nº oficio: 123/2026");
    expect(lines).toContain("Nº comprobación: 456/2026");
  });

  it("card helper muestra Nº notificación", () => {
    const lines = lineasIdentificadoresPendiente({
      ...baseRow,
      tipo_iniciador: "REINSPECCION_NOTIFICACION",
      identificadores: { numero_notificacion: "789", anio_notificacion: 2026 },
    });
    expect(lines).toContain("Nº notificación: 789/2026");
  });

  it("no renderiza líneas sin valor", () => {
    expect(lineasIdentificadoresPendiente(baseRow)).toEqual([]);
    expect(lineasIdentificadoresPendiente({ ...baseRow, identificadores: {} })).toEqual([]);
  });

  it("formatoNumeroConAnio sin año devuelve solo número", () => {
    expect(formatoNumeroConAnio("99", null)).toBe("99");
  });

  it("PlanificacionIniciadorCompactCard usa lineasIdentificadoresPendiente", () => {
    const src = read(
      "src/Containers/RutasTrabajo/planificacion/components/PlanificacionIniciadorCompactCard.tsx"
    );
    expect(src).toContain("lineasIdentificadoresPendiente");
    expect(src).toContain("identificadores.length > 0");
  });
});

describe("STAB-10c backend presenter", () => {
  it("ruta_presenters expone identificadores", () => {
    const src = read("../Backend/app/domains/rutas_trabajo/presenters/ruta_presenters.py");
    expect(src).toContain("_build_identificadores_iniciador");
    expect(src).toContain('"identificadores"');
  });
});
