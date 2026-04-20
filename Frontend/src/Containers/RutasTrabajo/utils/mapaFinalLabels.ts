/**
 * Etiquetas legibles para la vista Mapa final (sin exponer códigos de DB).
 */

const GEO_STATUS_LABELS: Record<string, string> = {
  OK: "Ubicación confirmada",
  PENDING: "Geocodificación pendiente",
  GEO_PENDING: "Geocodificación pendiente",
  NORM_PENDING: "Normalización de dirección pendiente",
  REVIEW: "Requiere revisión",
  NO_MATCH: "Sin coincidencia en mapa",
  ERROR: "Error al geocodificar",
};

/**
 * Convierte `geo_status` de domicilio_geocode a texto para operadores.
 *
 * @param raw — Valor tal como viene del API (p. ej. `OK`, `PENDING`).
 * @returns Texto humanizado, o `null` si no hay valor.
 */
export function humanizarGeoStatus(raw: string | null | undefined): string | null {
  if (raw == null || String(raw).trim() === "") return null;
  const k = String(raw).trim().toUpperCase();
  if (GEO_STATUS_LABELS[k]) return GEO_STATUS_LABELS[k];
  return String(raw)
    .split("_")
    .filter(Boolean)
    .map((w) => w.charAt(0) + w.slice(1).toLowerCase())
    .join(" ");
}
