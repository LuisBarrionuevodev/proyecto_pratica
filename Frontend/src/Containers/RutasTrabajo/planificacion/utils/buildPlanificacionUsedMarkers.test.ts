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

describe("buildPlanificacionUsedMarkers", () => {
  it("renderiza pin rojo para pool con coordenadas", () => {
    const markers = buildPlanificacionUsedMarkers({ poolItems: [pool()], grupos: [], itemsActivos: [] });
    expect(markers).toHaveLength(1);
    expect(markers[0].estado).toBe("pool");
  });

  it("prioriza grupo sobre pool para el mismo iniciador", () => {
    const grupos: IRutaGrupoMin[] = [{ id: 5, ruta_trabajo_id: 1, nombre: "Grupo A", estado: null, inspectores: [], created_by_user_id: 1, created_at: null, updated_at: null }];
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
      poolItems: [pool()],
      grupos,
      itemsActivos: items,
    });
    expect(markers).toHaveLength(1);
    expect(markers[0].estado).toBe("grupo");
    expect(markers[0].grupoNombre).toBe("Grupo A");
  });

  it("omite iniciadores sin coordenadas válidas", () => {
    const markers = buildPlanificacionUsedMarkers({
      poolItems: [pool({ lat: null, lng: null })],
      grupos: [],
      itemsActivos: [],
    });
    expect(markers).toHaveLength(0);
  });

  it("filtra por distrito activo cuando corresponde", () => {
    const markers = buildPlanificacionUsedMarkers({
      poolItems: [pool({ distrito_id: 10 }), pool({ pool_id: 2, iniciador_id: 11, iniciador_ruta_id: 11, distrito_id: 20 })],
      grupos: [],
      itemsActivos: [],
      distritoActivoId: 10,
    });
    expect(markers.map((m) => m.iniciadorId)).toEqual([10]);
  });
});
