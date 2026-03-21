import { useMemo } from "react";

import type { IRutaGrupoMin, IRutaIniciadorPendienteRow, IRutaItemMin } from "../../../api/rutasTrabajoApi";
import type { RutaMapaGrupoVista, RutaMapaItemVista, RutaMapaMarker, RutaMapaPolyline, UseRutaMapaResult } from "../types/rutasTrabajoMapa.types";

/** Mismo criterio de acento que `PanelGruposRuta`. */
export function grupoColorAccent(grupoId: number): string {
  return `hsl(${(grupoId * 61) % 360} 75% 58%)`;
}

function etiquetaItem(
  item: IRutaItemMin,
  iniciadorById: Record<number, IRutaIniciadorPendienteRow>
): string {
  const ini = iniciadorById[item.iniciador_ruta_id];
  const texto =
    ini?.domicilio_texto ??
    `${ini?.domicilio?.calle ?? "-"} ${ini?.domicilio?.numero ?? ""}`.trim();
  return texto || `Iniciador #${item.iniciador_ruta_id}`;
}

/**
 * Transforma grupos + ítems en estructura para panel Leaflet y leyendas.
 * Las coordenadas por ítem no vienen hoy en la API: lat/lng quedan null y no se dibujan markers/polylines.
 */
export function useRutaMapa(
  grupos: IRutaGrupoMin[],
  itemsActivos: IRutaItemMin[],
  iniciadorById: Record<number, IRutaIniciadorPendienteRow>
): UseRutaMapaResult {
  return useMemo(() => {
    const mapCenter: [number, number] = [-26.8241, -65.2226];
    const mapZoom = 13;

    const gruposVista: RutaMapaGrupoVista[] = grupos.map((g) => {
      const color = grupoColorAccent(g.id);
      const groupItems = itemsActivos
        .filter((it) => it.ruta_grupo_id === g.id)
        .sort((a, b) => a.id - b.id);

      const items: RutaMapaItemVista[] = groupItems.map((it, idx) => {
        // Reservado: si el backend expone lat/lng en item o iniciador, mapear aquí.
        const lat = null as number | null;
        const lng = null as number | null;
        return {
          itemId: it.id,
          iniciadorRutaId: it.iniciador_ruta_id,
          orden: idx + 1,
          etiqueta: etiquetaItem(it, iniciadorById),
          lat,
          lng,
        };
      });

      const inspectoresResumen =
        g.inspectores.length === 0
          ? "Sin inspectores"
          : g.inspectores
              .map((i) => i.inspector_nombre || `Inspector #${i.inspector_id}`)
              .join(", ");

      return {
        id: g.id,
        nombre: g.nombre,
        color,
        estado: g.estado,
        inspectoresResumen,
        itemCount: items.length,
        items,
      };
    });

    const markers: RutaMapaMarker[] = [];
    const polylines: RutaMapaPolyline[] = [];

    for (const gv of gruposVista) {
      const positions: [number, number][] = [];
      for (const it of gv.items) {
        if (it.lat != null && it.lng != null && !Number.isNaN(it.lat) && !Number.isNaN(it.lng)) {
          markers.push({
            itemId: it.itemId,
            grupoId: gv.id,
            orden: it.orden,
            lat: it.lat,
            lng: it.lng,
            etiqueta: it.etiqueta,
            color: gv.color,
          });
          positions.push([it.lat, it.lng]);
        }
      }
      if (positions.length >= 2) {
        polylines.push({ grupoId: gv.id, color: gv.color, positions });
      }
    }

    const tieneCoordenadas = markers.length > 0;
    const avisoCoordenadas = tieneCoordenadas
      ? null
      : "Los ítems de ruta aún no traen coordenadas desde la API. El mapa muestra el área de referencia (Tucumán). Cuando existan lat/lng, se dibujarán puntos y recorridos por grupo.";

    return {
      gruposVista,
      markers,
      polylines,
      mapCenter,
      mapZoom,
      tieneCoordenadas,
      avisoCoordenadas,
    };
  }, [grupos, itemsActivos, iniciadorById]);
}
