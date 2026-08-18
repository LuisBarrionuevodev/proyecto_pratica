import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import type { IRutaIniciadorPendienteRow } from "../../../api/rutasTrabajoApi";
import { buildEstablecimientoSecundario } from "./iniciadorDisplay";

const read = (rel: string) => readFileSync(resolve(process.cwd(), rel), "utf8");

const baseRelevamientoRow = {
  id: 1,
  tipo_iniciador: "RELEVAMIENTO",
  estado_iniciador: "PENDIENTE",
  fecha_origen: "2026-07-01",
  prioridad: 1,
  turno_sugerido: null,
  domicilio: {
    id: 10,
    calle: "San Martín",
    numero: "Y Maipú",
    distrito_id: 1,
    barrio_id: null,
    rubro: "Verdulería",
  },
  origen: {
    tipo: "RELEVAMIENTO",
    denuncia_id: null,
    relevamiento_id: 5,
    notificacion_id: null,
    oficio_id: null,
    actuacion_id: null,
  },
  observaciones: null,
  domicilio_texto: "San Martín Y Maipú",
  rubro_nombre: "Carnicería",
} satisfies IRutaIniciadorPendienteRow;

describe("PR7.9 buildEstablecimientoSecundario", () => {
  it("muestra nombre fantasía y ángulo cuando existen", () => {
    const line = buildEstablecimientoSecundario({
      nombre_fantasia: "El Toro",
      angulo_esquina: "NE",
    });
    expect(line).toBe("Nombre fantasía: El Toro · Esquina: NE");
  });

  it("muestra solo nombre si no hay ángulo", () => {
    expect(buildEstablecimientoSecundario({ nombre_fantasia: "El Toro" })).toBe(
      "Nombre fantasía: El Toro"
    );
  });

  it("muestra solo ángulo si no hay nombre", () => {
    expect(buildEstablecimientoSecundario({ angulo_esquina: "SO" })).toBe("Esquina: SO");
  });

  it("no muestra nada si ambos son null o vacíos", () => {
    expect(buildEstablecimientoSecundario({ nombre_fantasia: null, angulo_esquina: null })).toBeNull();
    expect(buildEstablecimientoSecundario({ nombre_fantasia: "  ", angulo_esquina: "" })).toBeNull();
  });

  it("distingue dos relevamientos misma esquina con distinto ángulo", () => {
    const a = buildEstablecimientoSecundario({
      nombre_fantasia: "El Toro",
      angulo_esquina: "NE",
    });
    const b = buildEstablecimientoSecundario({
      nombre_fantasia: "La Vaquita",
      angulo_esquina: "SO",
    });
    expect(a).not.toBe(b);
    expect(a).toContain("NE");
    expect(b).toContain("SO");
  });
});

describe("PR7.9 UI Ruta de Trabajo", () => {
  it("PlanificacionIniciadorCompactCard muestra EstablecimientoSecundarioLine", () => {
    const src = read(
      "src/Containers/RutasTrabajo/planificacion/components/PlanificacionIniciadorCompactCard.tsx"
    );
    expect(src).toContain("EstablecimientoSecundarioLine");
    expect(src).toContain('item={row}');
  });

  it("PoolDelDiaPanel muestra datos del pool backend", () => {
    const src = read("src/Containers/RutasTrabajo/planificacion/PoolDelDiaPanel.tsx");
    expect(src).toContain("poolDiaOrigenLabel");
    expect(src).toContain("domicilio_texto");
    expect(src).toContain("rubro_nombre");
  });

  it("popup mapa operativo muestra discriminadores", () => {
    const src = read(
      "src/Containers/RutasTrabajo/planificacion/components/PlanificacionMapaGeopuntoOperativaCard.tsx"
    );
    expect(src).toContain("EstablecimientoSecundarioLine");
    expect(src).toContain("rubroLineaPendiente(row)");
  });

  it("TablaIniciadoresPendientes muestra detalle operativo en columna dedicada", () => {
    const src = read("src/Containers/RutasTrabajo/Components/TablaIniciadoresPendientes.tsx");
    expect(src).toContain("detalleOperativoTexto");
    expect(src).toContain("ASIGNACION_COL_DETALLE_OPERATIVO");
  });

  it("tipos API incluyen nombre_fantasia y angulo_esquina", () => {
    const src = read("src/api/rutasTrabajoApi.ts");
    expect(src).toContain("nombre_fantasia?: string | null");
    expect(src).toContain("angulo_esquina?: string | null");
  });
});

describe("PR7.9 Completar Trabajo intacto", () => {
  it("completarTrabajoApi no define nombre_fantasia ni angulo_esquina de relevamiento", () => {
    const src = read("src/api/completarTrabajoApi.ts");
    expect(src).not.toContain("nombre_fantasia");
    expect(src).not.toContain("angulo_esquina");
  });

  it("buildCompletarTrabajoCierreBody no envía discriminadores de relevamiento", () => {
    const src = read("src/Containers/CompletarTrabajos/utils/buildCompletarTrabajoCierreBody.ts");
    expect(src).not.toContain("nombre_fantasia");
    expect(src).not.toContain("angulo_esquina");
  });

  it("CompletarTrabajoModal no muestra campos de relevamiento", () => {
    const src = read("src/Containers/CompletarTrabajos/components/CompletarTrabajoModal.tsx");
    expect(src).not.toContain("nombre_fantasia");
    expect(src).not.toContain("angulo_esquina");
  });
});

describe("PR7.9 fixture relevamiento", () => {
  it("fila de ejemplo con rubro y discriminadores", () => {
    const row: IRutaIniciadorPendienteRow = {
      ...baseRelevamientoRow,
      nombre_fantasia: "El Toro",
      angulo_esquina: "NE",
    };
    expect(row.rubro_nombre).toBe("Carnicería");
    expect(buildEstablecimientoSecundario(row)).toBe("Nombre fantasía: El Toro · Esquina: NE");
  });
});
