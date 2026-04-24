import { useMemo } from "react";

import type { IRutaGrupoMin, IRutaIniciadorPendienteRow, IRutaItemMin } from "../../../api/rutasTrabajoApi";
import {
  distritoOperativoDesdeItemYPool,
  etiquetaDomicilioDesdeItemYPool,
  rubroOperativoDesdeItemYPool,
  tipoEtiquetaDesdeItemYPool,
} from "../utils/rutaItemOperativoDesdeItemYPool";
import type {
  RutaMapaGrupoVista,
  RutaMapaInspectorFila,
  RutaMapaItemVista,
  RutaMapaMarker,
  RutaMapaPolyline,
  RutaMapaResumenTerritorial,
  UseRutaMapaResult,
} from "../types/rutasTrabajoMapa.types";
import { humanizarGeoStatus } from "../utils/mapaFinalLabels";
import {
  POLYLINE_DASH_BY_INDEX,
  POLYLINE_WEIGHT_BY_INDEX,
  buildGrupoCodigoPorId,
  grupoEstiloIndex,
  grupoNombreEnMapa,
} from "../utils/mapaRutaGrupoTrazado";

/** Mismo criterio de acento que `PanelGruposRuta`. */
export function grupoColorAccent(grupoId: number): string {
  return `hsl(${(grupoId * 61) % 360} 75% 58%)`;
}

function ordenTrabajoLabel(item: IRutaItemMin): string | null {
  const ot = item.orden_trabajo;
  if (!ot) return null;
  return `O. trabajo ${ot.numero_acta} · ${String(ot.mes).padStart(2, "0")}/${ot.anio}`;
}

function inspectoresFilasDesdeGrupo(g: IRutaGrupoMin): RutaMapaInspectorFila[] {
  return g.inspectores.map((i) => {
    const legajo = i.inspector_legajo?.trim() || null;
    const nom = i.inspector_nombre?.trim();
    if (nom) return { inspectorId: i.inspector_id, nombre: nom, legajo };
    if (legajo) return { inspectorId: i.inspector_id, nombre: `Leg. ${legajo}`, legajo: null };
    return { inspectorId: i.inspector_id, nombre: "Inspector sin datos", legajo: null };
  });
}

/**
 * Transforma grupos + ítems en estructura para panel Leaflet y leyendas.
 * lat/lng vienen del detail de ruta (domicilio_geocode); sin coords no se dibujan markers.
 *
 * Orden de direcciones (ítems): no hay secuencia explícita en modelo; se usa `id` ascendente (detail ordena igual).
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
        const poolRow = iniciadorById[it.iniciador_ruta_id];
        const lat = typeof it.lat === "number" && !Number.isNaN(it.lat) ? it.lat : null;
        const lng = typeof it.lng === "number" && !Number.isNaN(it.lng) ? it.lng : null;
        const rubroFull = rubroOperativoDesdeItemYPool(it, poolRow);
        const distritoFull = distritoOperativoDesdeItemYPool(it, poolRow);
        const tipoIniciadorLabel = tipoEtiquetaDesdeItemYPool(it, poolRow);
        const geoRaw = it.geo_status ?? null;
        return {
          itemId: it.id,
          iniciadorRutaId: it.iniciador_ruta_id,
          orden: idx + 1,
          etiqueta: etiquetaDomicilioDesdeItemYPool(it, poolRow),
          lat,
          lng,
          rubroNombre: rubroFull === "Sin rubro" ? null : rubroFull,
          distritoNombre: distritoFull,
          geoStatus: geoRaw,
          geoStatusLabel: humanizarGeoStatus(geoRaw),
          ordenTrabajoLabel: ordenTrabajoLabel(it),
          tipoIniciadorLabel,
        };
      });

      const filasInsp = inspectoresFilasDesdeGrupo(g);
      const inspectoresResumen =
        filasInsp.length === 0
          ? "Sin inspectores"
          : filasInsp.map((f) => (f.legajo ? `${f.nombre} (leg. ${f.legajo})` : f.nombre)).join(", ");

      return {
        id: g.id,
        nombre: g.nombre,
        color,
        estado: g.estado,
        inspectoresResumen,
        inspectoresFilas: filasInsp,
        itemCount: items.length,
        items,
      };
    });

    const markers: RutaMapaMarker[] = [];
    const polylines: RutaMapaPolyline[] = [];

    const grupoIdsSorted = [...grupos].map((g) => g.id).sort((a, b) => a - b);
    const codigoPorGrupo = buildGrupoCodigoPorId(grupoIdsSorted);

    for (const gv of gruposVista) {
      const gIdx = grupoEstiloIndex(gv.id, grupoIdsSorted);
      const grupoCodigo = codigoPorGrupo.get(gv.id) ?? `G${gIdx + 1}`;
      const dashPat = POLYLINE_DASH_BY_INDEX[gIdx % POLYLINE_DASH_BY_INDEX.length];
      const weight = POLYLINE_WEIGHT_BY_INDEX[gIdx % POLYLINE_WEIGHT_BY_INDEX.length];

      const positions: [number, number][] = [];
      for (const it of gv.items) {
        if (it.lat != null && it.lng != null && !Number.isNaN(it.lat) && !Number.isNaN(it.lng)) {
          markers.push({
            itemId: it.itemId,
            grupoId: gv.id,
            grupoCodigo,
            grupoStyleIndex: gIdx,
            nombreGrupo: gv.nombre,
            orden: it.orden,
            lat: it.lat,
            lng: it.lng,
            etiqueta: it.etiqueta,
            color: gv.color,
            rubroNombre: it.rubroNombre,
            distritoNombre: it.distritoNombre,
            geoStatus: it.geoStatus,
            geoStatusLabel: it.geoStatusLabel,
            ordenTrabajoLabel: it.ordenTrabajoLabel,
            tipoIniciadorLabel: it.tipoIniciadorLabel,
          });
          positions.push([it.lat, it.lng]);
        }
      }
      if (positions.length >= 2) {
        polylines.push({
          grupoId: gv.id,
          grupoCodigo,
          grupoNombreCorto: grupoNombreEnMapa(gv.nombre),
          color: gv.color,
          positions,
          dashArray: dashPat,
          weight,
        });
      }
    }

    const tieneCoordenadas = markers.length > 0;
    const avisoCoordenadas = tieneCoordenadas
      ? null
      : "Sin ubicaciones para dibujar. Mapa en zona de referencia. Revisar geocodificación o Asignación.";

    const distritosSet = new Set<string>();
    for (const gv of gruposVista) {
      for (const it of gv.items) {
        const d = it.distritoNombre?.trim();
        if (d) distritosSet.add(d);
      }
    }
    const distritosCubiertos = Array.from(distritosSet).sort((a, b) => a.localeCompare(b, "es"));
    const totalItems = itemsActivos.filter((i) => !i.deleted_at).length;
    const itemsConCoordenadas = markers.length;

    let hintCobertura: string | null = null;
    if (totalItems === 0) {
      hintCobertura = "Sin direcciones en grupos.";
    } else if (distritosCubiertos.length === 0) {
      hintCobertura = "Sin distrito en datos.";
    } else if (distritosCubiertos.length === 1) {
      hintCobertura = distritosCubiertos[0];
    } else {
      hintCobertura = `${distritosCubiertos.length} distritos`;
    }

    const resumenTerritorial: RutaMapaResumenTerritorial = {
      totalItems,
      itemsConCoordenadas,
      distritosCubiertos,
      hintCobertura,
    };

    return {
      gruposVista,
      markers,
      polylines,
      mapCenter,
      mapZoom,
      tieneCoordenadas,
      avisoCoordenadas,
      resumenTerritorial,
    };
  }, [grupos, itemsActivos, iniciadorById]);
}
