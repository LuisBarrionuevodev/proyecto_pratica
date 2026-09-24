/**
 * PR7.11 — Integración liviana del flujo multi-establecimiento (UI + PDF builder).
 */

import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import type { IRutaGrupoMin, IRutaItemMin, IRutaTrabajo } from "../../api/rutasTrabajoApi";
import { buildRutaPublicadaDocumentModel } from "./buildRutaPublicadaDocumentModel";
import { buildBloqueDireccionOperativaPdf } from "../utils/establecimientoSecundario";

const read = (rel: string) => readFileSync(resolve(process.cwd(), rel), "utf8");

const rutaBase: IRutaTrabajo = {
  id: 1,
  fecha: "2026-07-11",
  turno: "MANIANA",
  estado_ruta: "PUBLICADA",
  numero: 3,
  observaciones: null,
  created_by_user_id: 1,
  created_at: null,
  updated_at: null,
};

const grupoBase: IRutaGrupoMin = {
  id: 10,
  ruta_trabajo_id: 1,
  nombre: "Grupo 1",
  estado: "ACTIVO",
  inspectores: [
    { id: 1, inspector_id: 100, inspector_nombre: "Pérez, Juan", inspector_legajo: "1234" },
  ],
  created_by_user_id: 1,
  created_at: null,
  updated_at: null,
};

function itemEsquina(
  id: number,
  rubro: string,
  fantasia: string,
  angulo: string,
  distrito = "Centro"
): IRutaItemMin {
  return {
    id,
    ruta_trabajo_id: 1,
    ruta_grupo_id: 10,
    iniciador_ruta_id: 200 + id,
    tipo_iniciador: "RELEVAMIENTO",
    orden_trabajo_id: null,
    actuacion_id: null,
    orden_trabajo: null,
    estado_ruta_item: "ASIGNADO",
    deleted_at: null,
    domicilio_texto: "San Martín Y Maipú",
    distrito_nombre: distrito,
    rubro_nombre: rubro,
    nombre_fantasia: fantasia,
    angulo_esquina: angulo,
  };
}

describe("PR7.11 flujo PDF esquina multi-establecimiento", () => {
  it("resumen incluye línea secundaria para ambos ítems", () => {
    const items = [
      itemEsquina(1, "Carnicería", "El Toro", "NE"),
      itemEsquina(2, "Verdulería", "La Huerta", "SO"),
    ];
    const model = buildRutaPublicadaDocumentModel(rutaBase, [grupoBase], items);
    const filas = model.grupos[0]?.items ?? [];
    expect(filas[0]?.establecimientoSecundario).toBe("Nombre fantasía: El Toro · Esquina: NE");
    expect(filas[1]?.establecimientoSecundario).toBe("Nombre fantasía: La Huerta · Esquina: SO");
  });

  it("órdenes de salida: distritos únicos aunque haya varios ítems", () => {
    const items = [
      itemEsquina(1, "Carnicería", "El Toro", "NE", "Distrito 10"),
      itemEsquina(2, "Verdulería", "La Huerta", "SO", "Distrito 10"),
    ];
    const model = buildRutaPublicadaDocumentModel(rutaBase, [grupoBase], items);
    expect(model.inspectoresSalida[0]?.distritosTexto).toBe("Distrito 10");
  });

  it("bloques PDF orden salida esperados literales", () => {
    const bloqueA = buildBloqueDireccionOperativaPdf({
      domicilio_texto: "San Martín Y Maipú",
      rubro_nombre: "Carnicería",
      nombre_fantasia: "El Toro",
      angulo_esquina: "NE",
    });
    const bloqueB = buildBloqueDireccionOperativaPdf({
      domicilio_texto: "San Martín Y Maipú",
      rubro_nombre: "Verdulería",
      nombre_fantasia: "La Huerta",
      angulo_esquina: "SO",
    });
    expect(bloqueA).toBe("San Martín Y Maipú\nÁngulo: NE");
    expect(bloqueB).toBe("San Martín Y Maipú\nÁngulo: SO");
  });
});

describe("PR7.11 UI Ruta de Trabajo", () => {
  it("pool y cards usan EstablecimientoSecundarioLine", () => {
    const pool = read("src/Containers/RutasTrabajo/planificacion/PoolDelDiaPanel.tsx");
    const card = read(
      "src/Containers/RutasTrabajo/planificacion/components/PlanificacionIniciadorCompactCard.tsx"
    );
    const popup = read(
      "src/Containers/RutasTrabajo/planificacion/components/PlanificacionMapaGeopuntoOperativaCard.tsx"
    );
    expect(pool).toContain("EstablecimientoSecundarioLine");
    expect(card).toContain("EstablecimientoSecundarioLine");
    expect(popup).toContain("EstablecimientoSecundarioLine");
  });

  it("Completar Trabajo sin campos fantasía/ángulo", () => {
    const modal = read("src/Containers/CompletarTrabajos/components/CompletarTrabajoModal.tsx");
    expect(modal).not.toContain("nombre_fantasia");
    expect(modal).not.toContain("angulo_esquina");
  });
});
