import { describe, expect, it } from "vitest";

import type { IRutaGrupoMin, IRutaIniciadorPendienteRow, IRutaItemMin } from "../../../../api/rutasTrabajoApi";
import type { IRutaPoolDiaRow } from "../../../../api/rutaPoolDiaApi";
import { poolDiaRowToIniciadorPendiente } from "../../utils/poolDiaDisplay";
import { buildPlanificacionUsedMarkers } from "./buildPlanificacionUsedMarkers";

function poolRow(overrides: Partial<IRutaPoolDiaRow> = {}): IRutaPoolDiaRow {
  return {
    pool_id: 1,
    fecha: "2026-05-19",
    estado: "EN_POOL",
    iniciador_id: 10,
    iniciador_ruta_id: 10,
    lat: -26.82,
    lng: -65.22,
    geo_status: "OK",
    domicilio_texto: "Calle 1",
    rubro_nombre: "Panadería",
    ...overrides,
  };
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

describe("OPER-RUTA.FUNCIONAL-2A.1 — pool autónomo para markers", () => {
  it("adapter conserva lat/lng del payload pool", () => {
    const adapted = poolDiaRowToIniciadorPendiente(
      poolRow({ lat: -26.824, lng: -65.221, geo_status: "OK" })
    );
    expect(adapted.lat).toBe(-26.824);
    expect(adapted.lng).toBe(-65.221);
  });

  it("pool puro con coords genera marker sin candidatos M4", () => {
    const poolItem = poolRow({ distrito_id: 10 });
    const markers = buildPlanificacionUsedMarkers({
      poolItems: [poolItem],
      grupos: [],
      itemsActivos: [],
      poolRowsById: {
        10: poolDiaRowToIniciadorPendiente(poolItem),
      },
      candidatosByIniciadorId: {},
    });
    expect(markers).toHaveLength(1);
    expect(markers[0].estado).toBe("pool");
    expect(markers[0].lat).toBe(-26.82);
  });

  it("reload conceptual: pool API con coords basta sin pendientesParaMapa", () => {
    const poolItem = poolRow({
      pool_id: 99,
      iniciador_id: 77,
      iniciador_ruta_id: 77,
      lat: -26.91,
      lng: -65.31,
      distrito_id: 10,
    });
    const markers = buildPlanificacionUsedMarkers({
      poolItems: [poolItem],
      grupos: [],
      itemsActivos: [],
      poolRowsById: {
        77: poolDiaRowToIniciadorPendiente(poolItem),
      },
      candidatosByIniciadorId: {},
    });
    expect(markers).toHaveLength(1);
    expect(markers[0].iniciadorId).toBe(77);
    expect(markers[0].lng).toBe(-65.31);
  });

  it("fallback defensivo: poolRowsById sin coords usa candidato M4", () => {
    const poolItem = poolRow({ lat: null, lng: null });
    const candidato: IRutaIniciadorPendienteRow = {
      id: 10,
      tipo_iniciador: "DENUNCIA",
      estado_iniciador: "PENDIENTE",
      fecha_origen: null,
      prioridad: 1,
      turno_sugerido: null,
      domicilio: {
        id: 1,
        calle: "X",
        numero: "1",
        distrito_id: 10,
        barrio_id: null,
      },
      origen: {
        tipo: null,
        denuncia_id: null,
        relevamiento_id: null,
        notificacion_id: null,
        oficio_id: null,
        actuacion_id: null,
      },
      observaciones: null,
      lat: -26.99,
      lng: -65.99,
    };
    const markers = buildPlanificacionUsedMarkers({
      poolItems: [poolItem],
      grupos: [],
      itemsActivos: [],
      poolRowsById: {
        10: poolDiaRowToIniciadorPendiente(poolItem),
      },
      candidatosByIniciadorId: { 10: candidato },
    });
    expect(markers).toHaveLength(1);
    expect(markers[0].lat).toBe(-26.99);
  });

  it("omite marker si ninguna fuente tiene coords", () => {
    const poolItem = poolRow({ lat: null, lng: null });
    const markers = buildPlanificacionUsedMarkers({
      poolItems: [poolItem],
      grupos: [],
      itemsActivos: [],
      poolRowsById: {
        10: poolDiaRowToIniciadorPendiente(poolItem),
      },
      candidatosByIniciadorId: {},
    });
    expect(markers).toHaveLength(0);
  });

  it("grupo sigue funcionando con coords propias", () => {
    const items: IRutaItemMin[] = [
      {
        id: 99,
        ruta_trabajo_id: 1,
        ruta_grupo_id: 5,
        iniciador_ruta_id: 20,
        estado_ruta_item: "PENDIENTE",
        deleted_at: null,
        lat: -26.83,
        lng: -65.23,
      },
    ];
    const markers = buildPlanificacionUsedMarkers({
      poolItems: [],
      grupos: [grupoA],
      itemsActivos: items,
      candidatosByIniciadorId: {},
    });
    expect(markers).toHaveLength(1);
    expect(markers[0].estado).toBe("grupo");
  });

  it("no duplica marker pool+grupo (prioridad grupo)", () => {
    const poolItem = poolRow();
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
      },
    ];
    const markers = buildPlanificacionUsedMarkers({
      poolItems: [poolItem],
      grupos: [grupoA],
      itemsActivos: items,
    });
    expect(markers).toHaveLength(1);
    expect(markers[0].estado).toBe("grupo");
  });
});
