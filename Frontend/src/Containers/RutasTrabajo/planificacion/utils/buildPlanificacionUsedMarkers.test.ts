import { describe, expect, it } from "vitest";

import type { IRutaGrupoMin, IRutaItemMin } from "../../../../api/rutasTrabajoApi";
import type { IRutaPoolDiaRow } from "../../../../api/rutaPoolDiaApi";
import { buildPlanificacionUsedMarkers } from "./buildPlanificacionUsedMarkers";

function pool(overrides: Partial<IRutaPoolDiaRow> = {}): IRutaPoolDiaRow {
  return {
    pool_id: 1,
    fecha: "2026-05-19",
    estado: "EN_POOL",
    iniciador_id: 10,
    iniciador_ruta_id: 10,
    lat: -26.82,
    lng: -65.22,
    domicilio_texto: "Calle 1",
    rubro_nombre: "Panadería",
    ...overrides,
  } as IRutaPoolDiaRow;
}

const grupoA: IRutaGrupoMin = {
  id: 5,
  ruta_trabajo_id: 1,
  nombre: "Grupo A",
  estado: null,
  inspectores: [],
  created_by_user_id: 1,
  created_at: null,
  updated_at: null,
};

describe("buildPlanificacionUsedMarkers — OPER-RUTA.FUNCIONAL-2A", () => {
  it("caso 1: pool del distrito activo aparece", () => {
    const markers = buildPlanificacionUsedMarkers({
      poolItems: [pool({ distrito_id: 10 })],
      grupos: [],
      itemsActivos: [],
    });
    expect(markers).toHaveLength(1);
    expect(markers[0].iniciadorId).toBe(10);
    expect(markers[0].estado).toBe("pool");
  });

  it("caso 2: pool de otro distrito aparece aunque el contexto sea otro", () => {
    const markers = buildPlanificacionUsedMarkers({
      poolItems: [pool({ distrito_id: 10 })],
      grupos: [],
      itemsActivos: [],
    });
    expect(markers.map((m) => m.iniciadorId)).toEqual([10]);
  });

  it("caso 3: pool con coords aparece sin filtro territorial en el builder", () => {
    const markers = buildPlanificacionUsedMarkers({
      poolItems: [pool({ distrito_id: 10 })],
      grupos: [],
      itemsActivos: [],
    });
    expect(markers).toHaveLength(1);
  });

  it("caso 4: grupo de otro distrito aparece", () => {
    const items: IRutaItemMin[] = [
      {
        id: 99,
        ruta_trabajo_id: 1,
        ruta_grupo_id: 5,
        iniciador_ruta_id: 20,
        estado_ruta_item: "PENDIENTE",
        deleted_at: null,
        distrito_id: 10,
        lat: -26.83,
        lng: -65.23,
        domicilio_texto: "Calle grupo",
      } as IRutaItemMin,
    ];
    const markers = buildPlanificacionUsedMarkers({
      poolItems: [],
      grupos: [grupoA],
      itemsActivos: items,
    });
    expect(markers).toHaveLength(1);
    expect(markers[0].iniciadorId).toBe(20);
    expect(markers[0].estado).toBe("grupo");
  });

  it("caso 5: grupo con coords aparece sin filtro territorial en el builder", () => {
    const items: IRutaItemMin[] = [
      {
        id: 100,
        ruta_trabajo_id: 1,
        ruta_grupo_id: 5,
        iniciador_ruta_id: 21,
        estado_ruta_item: "PENDIENTE",
        deleted_at: null,
        distrito_id: 10,
        lat: -26.84,
        lng: -65.24,
      } as IRutaItemMin,
    ];
    const markers = buildPlanificacionUsedMarkers({
      poolItems: [],
      grupos: [grupoA],
      itemsActivos: items,
    });
    expect(markers).toHaveLength(1);
  });

  it("caso 7: deduplicación grupo > pool para el mismo iniciadorId", () => {
    const items: IRutaItemMin[] = [
      {
        id: 99,
        ruta_trabajo_id: 1,
        ruta_grupo_id: 5,
        iniciador_ruta_id: 10,
        estado_ruta_item: "PENDIENTE",
        deleted_at: null,
        lat: -26.83,
        lng: -65.23,
        domicilio_texto: "Calle grupo",
      } as IRutaItemMin,
    ];
    const markers = buildPlanificacionUsedMarkers({
      poolItems: [pool({ distrito_id: 10 })],
      grupos: [grupoA],
      itemsActivos: items,
    });
    expect(markers).toHaveLength(1);
    expect(markers[0].estado).toBe("grupo");
    expect(markers[0].grupoNombre).toBe("Grupo A");
  });

  it("incluye pool y grupo de distintos distritos en la misma corrida", () => {
    const markers = buildPlanificacionUsedMarkers({
      poolItems: [
        pool({ pool_id: 1, iniciador_id: 10, iniciador_ruta_id: 10, distrito_id: 10 }),
        pool({ pool_id: 2, iniciador_id: 11, iniciador_ruta_id: 11, distrito_id: 20 }),
      ],
      grupos: [],
      itemsActivos: [],
    });
    expect(markers.map((m) => m.iniciadorId).sort()).toEqual([10, 11]);
  });

  it("omite iniciadores sin coordenadas válidas", () => {
    const markers = buildPlanificacionUsedMarkers({
      poolItems: [pool({ lat: null, lng: null })],
      grupos: [],
      itemsActivos: [],
    });
    expect(markers).toHaveLength(0);
  });
});
