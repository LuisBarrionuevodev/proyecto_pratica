import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import type { IRutaIniciadorPendienteRow } from "../../api/rutasTrabajoApi";
import type { IRutaPoolDiaRow } from "../../api/rutaPoolDiaApi";
import {
  ASIGNACION_COL_DETALLE_OPERATIVO,
  ASIGNACION_COL_DOMICILIO_RUBRO,
  ASIGNACION_COL_TIPO_PRIORIDAD,
  domicilioLineaAsignacion,
  prioridadDisplayOperativo,
  rubroLineaAsignacion,
  tipoLabelOperativo,
} from "./utils/asignacionTableDisplay";
import { detalleOperativoTexto } from "./utils/iniciadorDetalleOperativo";
import { poolDiaRowToIniciadorPendiente } from "./utils/poolDiaDisplay";

const read = (rel: string) => readFileSync(resolve(process.cwd(), rel), "utf8");

function poolRow(overrides: Partial<IRutaPoolDiaRow> = {}): IRutaPoolDiaRow {
  return {
    pool_id: 1,
    fecha: "2026-08-01",
    estado: "EN_POOL",
    origen_tipo: "INICIADOR",
    iniciador_id: 10,
    iniciador_ruta_id: 10,
    tipo_iniciador: "REINSPECCION_NOTIFICACION",
    tipo_iniciador_label: "Reinspección por notificación",
    prioridad: 3,
    prioridad_categoria: "ALTA",
    detalle_operativo_texto: "Notif.: 222/2026 · Prórroga: 10 días",
    domicilio_texto: "Av. Corrientes 1234",
    rubro_nombre: "Panadería",
    ...overrides,
  };
}

describe("RUTA-ASIG.2 asignacionTableDisplay", () => {
  it("muestra tipo correcto desde label del backend", () => {
    const row = poolDiaRowToIniciadorPendiente(poolRow());
    expect(tipoLabelOperativo(row)).toBe("Reinspección por notificación");
  });

  it("muestra prioridad Alta cuando existe", () => {
    const row = poolDiaRowToIniciadorPendiente(poolRow({ prioridad: 3, prioridad_categoria: "ALTA" }));
    expect(prioridadDisplayOperativo(row)?.label).toBe("Alta");
  });

  it("sin prioridad real devuelve null (UI muestra —)", () => {
    const row = poolDiaRowToIniciadorPendiente(
      poolRow({ prioridad: null, prioridad_categoria: undefined, prioridad_label: null })
    );
    expect(prioridadDisplayOperativo(row)).toBeNull();
  });

  it("domicilio / rubro combina dirección y rubro", () => {
    const row = poolDiaRowToIniciadorPendiente(poolRow());
    expect(domicilioLineaAsignacion(row)).toContain("Corrientes");
    expect(rubroLineaAsignacion(row)).toBe("Panadería");
  });

  it("detalle operativo sigue disponible", () => {
    const row = poolDiaRowToIniciadorPendiente(poolRow());
    expect(detalleOperativoTexto(row)).toContain("Notif.: 222/2026");
  });
});

describe("RUTA-ASIG.2 TablaIniciadoresPendientes columnas", () => {
  const tabla = read("src/Containers/RutasTrabajo/Components/TablaIniciadoresPendientes.tsx");

  it("muestra columna Tipo / prioridad", () => {
    expect(tabla).toContain("ASIGNACION_COL_TIPO_PRIORIDAD");
    expect(tabla).toContain("prioridadDisplayOperativo");
  });

  it("no muestra columnas separadas Tipo, Prioridad, Domicilio, Rubro ni Estado", () => {
    expect(tabla).not.toMatch(/header:\s*"Estado"/);
    expect(tabla).not.toMatch(/header:\s*"Tipo",/);
    expect(tabla).not.toMatch(/header:\s*"Prioridad"/);
    expect(tabla).not.toMatch(/header:\s*"Domicilio"/);
    expect(tabla).not.toMatch(/header:\s*"Rubro"/);
  });

  it("mantiene Detalle operativo", () => {
    expect(tabla).toContain("ASIGNACION_COL_DETALLE_OPERATIVO");
    expect(tabla).toContain("detalleOperativoTexto");
  });

  it("muestra columna Domicilio / rubro", () => {
    expect(tabla).toContain("ASIGNACION_COL_DOMICILIO_RUBRO");
    expect(tabla).toContain("domicilioLineaAsignacion");
    expect(tabla).toContain("rubroLineaAsignacion");
  });
});

describe("RUTA-ASIG.2 grupos asignados", () => {
  it("PanelGruposRuta conserva detalle operativo en ítems", () => {
    const panel = read("src/Containers/RutasTrabajo/Components/PanelGruposRuta.tsx");
    expect(panel).toContain("detalleOperativoTexto");
  });
});

describe("RUTA-ASIG.2 tipos variados", () => {
  const casos: Array<{ tipo: string; label: string; detalle: string }> = [
    {
      tipo: "REINSPECCION_NOTIFICACION",
      label: "Reinspección por notificación",
      detalle: "Notif.: 1/2026",
    },
    {
      tipo: "REINSPECCION_OFICIO",
      label: "Reinspección por oficio",
      detalle: "Oficio: 88/2026",
    },
    {
      tipo: "DENUNCIA",
      label: "Denuncia",
      detalle: "Motivo: Basura",
    },
    {
      tipo: "RELEVAMIENTO",
      label: "Relevamiento",
      detalle: "Relevamiento",
    },
  ];

  for (const c of casos) {
    it(`${c.tipo} muestra tipo y detalle`, () => {
      const row = poolDiaRowToIniciadorPendiente(
        poolRow({
          tipo_iniciador: c.tipo,
          tipo_iniciador_label: c.label,
          detalle_operativo_texto: c.detalle,
        })
      );
      expect(tipoLabelOperativo(row)).toBe(c.label);
      expect(detalleOperativoTexto(row)).toContain(c.detalle.split(":")[0]);
    });
  }
});

describe("RUTA-ASIG.2 prioridad por categoría sin número", () => {
  it("usa prioridad_categoria del backend", () => {
    const row = {
      id: 1,
      tipo_iniciador: "DENUNCIA",
      estado_iniciador: "PENDIENTE",
      fecha_origen: null,
      prioridad: null,
      prioridad_categoria: "MEDIA" as const,
      turno_sugerido: null,
      domicilio: null,
      origen: {
        tipo: null,
        denuncia_id: null,
        relevamiento_id: null,
        notificacion_id: null,
        oficio_id: null,
        actuacion_id: null,
      },
      observaciones: null,
    } satisfies IRutaIniciadorPendienteRow;
    expect(prioridadDisplayOperativo(row)?.label).toBe("Media");
  });
});
