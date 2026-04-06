import type { IRutaIniciadorPendienteRow } from "../../../../api/rutasTrabajoApi";

/**
 * Normaliza lat/lng del row de planificación (number o string en JSON).
 */
export function parseIniciadorLatLng(row: IRutaIniciadorPendienteRow): { lat: number; lng: number } | null {
  const rawLat = row.lat as unknown;
  const rawLng = row.lng as unknown;
  const lat =
    typeof rawLat === "number"
      ? rawLat
      : typeof rawLat === "string" && rawLat.trim() !== ""
        ? Number.parseFloat(rawLat)
        : NaN;
  const lng =
    typeof rawLng === "number"
      ? rawLng
      : typeof rawLng === "string" && rawLng.trim() !== ""
        ? Number.parseFloat(rawLng)
        : NaN;
  if (!Number.isFinite(lat) || !Number.isFinite(lng)) return null;
  return { lat, lng };
}
