import type { IRutaGrupoMin, IRutaIniciadorPendienteRow, IRutaItemMin } from "../../../../api/rutasTrabajoApi";
import type { IRutaPoolDiaRow } from "../../../../api/rutaPoolDiaApi";
import { tipoLabelOperativo } from "../../utils/iniciadorDetalleOperativo";
import { parseIniciadorLatLng } from "./iniciadorCoords";

export type PlanificacionUsedMarkerEstado = "pool" | "grupo";

export type PlanificacionUsedMarker = {
  iniciadorId: number;
  lat: number;
  lng: number;
  estado: PlanificacionUsedMarkerEstado;
  grupoNombre?: string | null;
  tipoLabel: string;
  domicilio: string;
  rubro: string;
};

type LatLngSource = { lat?: number | null; lng?: number | null };

function parseLatLng(source: LatLngSource | null | undefined): { lat: number; lng: number } | null {
  if (!source) return null;
  const asRow = source as IRutaIniciadorPendienteRow;
  if ("tipo_iniciador" in asRow || "domicilio_texto" in asRow) {
    return parseIniciadorLatLng(asRow);
  }
  const lat = source.lat;
  const lng = source.lng;
  if (typeof lat !== "number" || typeof lng !== "number") return null;
  if (!Number.isFinite(lat) || !Number.isFinite(lng)) return null;
  return { lat, lng };
}

function resolveIniciadorId(pool: IRutaPoolDiaRow): number | null {
  const id = Number(pool.iniciador_id ?? pool.iniciador_ruta_id);
  return Number.isFinite(id) && id > 0 ? id : null;
}

function resolveCoords(
  primary: LatLngSource | null | undefined,
  fallback?: IRutaIniciadorPendienteRow | null
): { lat: number; lng: number } | null {
  return parseLatLng(primary) ?? (fallback ? parseIniciadorLatLng(fallback) : null);
}

function matchesDistrito(
  distritoId: number | null | undefined,
  distritoActivoId: number | null | undefined
): boolean {
  if (distritoActivoId == null) return true;
  if (distritoId == null) return true;
  return distritoId === distritoActivoId;
}

export type BuildPlanificacionUsedMarkersInput = {
  poolItems: IRutaPoolDiaRow[];
  grupos: IRutaGrupoMin[];
  itemsActivos: IRutaItemMin[];
  poolRowsById?: Record<number, IRutaIniciadorPendienteRow>;
  candidatosByIniciadorId?: Record<number, IRutaIniciadorPendienteRow>;
  distritoActivoId?: number | null;
};

/**
 * Pines rojos de iniciadores ya agregados a la ruta (pool / grupo), deduplicados con prioridad grupo.
 */
export function buildPlanificacionUsedMarkers({
  poolItems,
  grupos,
  itemsActivos,
  poolRowsById = {},
  candidatosByIniciadorId = {},
  distritoActivoId = null,
}: BuildPlanificacionUsedMarkersInput): PlanificacionUsedMarker[] {
  const byId = new Map<number, PlanificacionUsedMarker>();
  const grupoById = new Map(grupos.map((g) => [g.id, g]));

  for (const pool of poolItems) {
    const iniId = resolveIniciadorId(pool);
    if (iniId == null) continue;
    if (!matchesDistrito(pool.distrito_id, distritoActivoId)) continue;

    const fallback = poolRowsById[iniId] ?? candidatosByIniciadorId[iniId];
    const coords = resolveCoords(pool, fallback);
    if (!coords) continue;

    byId.set(iniId, {
      iniciadorId: iniId,
      lat: coords.lat,
      lng: coords.lng,
      estado: "pool",
      tipoLabel: tipoLabelOperativo(pool),
      domicilio: pool.domicilio_texto?.trim() || fallback?.domicilio_texto?.trim() || "—",
      rubro: pool.rubro_nombre?.trim() || fallback?.rubro_nombre?.trim() || "—",
    });
  }

  for (const item of itemsActivos) {
    const iniId = item.iniciador_ruta_id;
    if (!iniId) continue;
    if (!matchesDistrito(item.distrito_id, distritoActivoId)) continue;

    const fallback = poolRowsById[iniId] ?? candidatosByIniciadorId[iniId];
    const coords = resolveCoords(item, fallback);
    if (!coords) continue;

    const grupo = grupoById.get(item.ruta_grupo_id);
    byId.set(iniId, {
      iniciadorId: iniId,
      lat: coords.lat,
      lng: coords.lng,
      estado: "grupo",
      grupoNombre: grupo?.nombre ?? null,
      tipoLabel: tipoLabelOperativo(item),
      domicilio: item.domicilio_texto?.trim() || fallback?.domicilio_texto?.trim() || "—",
      rubro: item.rubro_nombre?.trim() || fallback?.rubro_nombre?.trim() || "—",
    });
  }

  return Array.from(byId.values());
}
