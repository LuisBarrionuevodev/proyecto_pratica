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
  if (item.domicilio_texto?.trim()) {
    return item.domicilio_texto.trim();
  }
  const ini = iniciadorById[item.iniciador_ruta_id];
  const texto =
    ini?.domicilio_texto ??
    `${ini?.domicilio?.calle ?? "-"} ${ini?.domicilio?.numero ?? ""}`.trim();
  return texto || `Iniciador #${item.iniciador_ruta_id}`;
}

function ordenTrabajoLabel(item: IRutaItemMin): string | null {
  const ot = item.orden_trabajo;
  if (!ot) return null;
  return `OT ${ot.numero_acta} · ${String(ot.mes).padStart(2, "0")}/${ot.anio}`;
}

/**
 * Transforma grupos + ítems en estructura para panel Leaflet y leyendas.
 * lat/lng vienen del detail de ruta (domicilio_geocode); sin coords no se dibujan markers.
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
        const lat = typeof it.lat === "number" && !Number.isNaN(it.lat) ? it.lat : null;
        const lng = typeof it.lng === "number" && !Number.isNaN(it.lng) ? it.lng : null;
        return {
          itemId: it.id,
          iniciadorRutaId: it.iniciador_ruta_id,
          orden: idx + 1,
          etiqueta: etiquetaItem(it, iniciadorById),
          lat,
          lng,
          rubroNombre: it.rubro_nombre ?? null,
          distritoNombre: it.distrito_nombre ?? null,
          geoStatus: it.geo_status ?? null,
          ordenTrabajoLabel: ordenTrabajoLabel(it),
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
            rubroNombre: it.rubroNombre,
            distritoNombre: it.distritoNombre,
            geoStatus: it.geoStatus,
            ordenTrabajoLabel: it.ordenTrabajoLabel,
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
      : "Ningún ítem tiene lat/lng en geocodificación (domicilio_geocode). El mapa muestra el área de referencia (Tucumán). Con coords válidas se dibujan puntos y líneas simples por orden de ítem en cada grupo.";

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
