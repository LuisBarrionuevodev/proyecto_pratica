import { describe, expect, it } from "vitest";

import type { IRutaGrupoMin, IRutaItemMin } from "../../../api/rutasTrabajoApi";
import { evaluarPublicacionRuta } from "./rutaPublicarReadiness";

function grupo(partial: Partial<IRutaGrupoMin> & Pick<IRutaGrupoMin, "id" | "nombre">): IRutaGrupoMin {
  return {
    ruta_trabajo_id: 1,
    estado: "ACTIVO",
    inspectores: [],
    items: [],
    ...partial,
  };
}

function item(partial: Partial<IRutaItemMin> & Pick<IRutaItemMin, "id" | "ruta_grupo_id">): IRutaItemMin {
  return {
    ruta_trabajo_id: 1,
    iniciador_ruta_id: partial.id,
    estado_ruta_item: "ASIGNADO",
    ...partial,
  };
}

describe("evaluarPublicacionRuta", () => {
  it("bloquea si un grupo tiene menos de 2 inspectores", () => {
    const grupos = [grupo({ id: 1, nombre: "Grupo 1", inspectores: [{ id: 1, inspector_id: 10 }] })];
    const items = [item({ id: 100, ruta_grupo_id: 1, orden_trabajo_id: 5 })];
    const r = evaluarPublicacionRuta(grupos, items);
    expect(r.puedePublicar).toBe(false);
    expect(r.blockers.some((b) => b.includes("2 inspectores"))).toBe(true);
  });

  it("bloquea si falta OT guardada", () => {
    const grupos = [
      grupo({
        id: 1,
        nombre: "Grupo 1",
        inspectores: [
          { id: 1, inspector_id: 10 },
          { id: 2, inspector_id: 11 },
        ],
      }),
    ];
    const items = [item({ id: 100, ruta_grupo_id: 1, orden_trabajo_id: null, domicilio_texto: "Calle 1" })];
    const r = evaluarPublicacionRuta(grupos, items);
    expect(r.puedePublicar).toBe(false);
    expect(r.blockers.some((b) => b.includes("Falta guardar la OT"))).toBe(true);
  });

  it("permite publicar cuando hay 2 inspectores y OT en cada ítem", () => {
    const grupos = [
      grupo({
        id: 1,
        nombre: "Grupo 1",
        inspectores: [
          { id: 1, inspector_id: 10 },
          { id: 2, inspector_id: 11 },
        ],
      }),
    ];
    const items = [item({ id: 100, ruta_grupo_id: 1, orden_trabajo_id: 5 })];
    const r = evaluarPublicacionRuta(grupos, items);
    expect(r.puedePublicar).toBe(true);
    expect(r.blockers).toEqual([]);
  });
});
