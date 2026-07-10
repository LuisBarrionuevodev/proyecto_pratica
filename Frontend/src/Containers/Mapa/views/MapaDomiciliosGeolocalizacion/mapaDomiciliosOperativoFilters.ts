import type { GestionDomiciliosMapMode, GestionDomiciliosStatusOperativo } from "../../../../api/gestionDomiciliosApi";

export type GestionDomiciliosFiltroOption = {
  value: GestionDomiciliosStatusOperativo;
  label: string;
};

/** Filtros operativos visibles al operador (sin slices técnicos). Dropdown legacy. */
export const GESTION_DOMICILIOS_FILTROS: GestionDomiciliosFiltroOption[] = [
  { value: "requiere_accion", label: "Requieren acción" },
  { value: "sin_punto", label: "Sin punto" },
  { value: "punto_dudoso", label: "Punto dudoso" },
  { value: "manual", label: "Manuales" },
  { value: "geolocalizado", label: "Geolocalizados" },
  { value: "todos", label: "Todos" },
];

/**
 * Subtabs operativas en Mapa (PR6C.14).
 * Mapeo sin cambios de backend:
 * - Para revisar → requiere_accion (cola que requiere acción del operador)
 * - En el mapa → geolocalizado (domicilios con punto visible en mapa)
 * - Validados → manual (ubicación confirmada manualmente por inspector)
 * - Todos → todos
 */
export const MAPA_DOMICILIOS_SUBTABS: GestionDomiciliosFiltroOption[] = [
  { value: "requiere_accion", label: "Para revisar" },
  { value: "geolocalizado", label: "En el mapa" },
  { value: "manual", label: "Validados" },
  { value: "todos", label: "Todos" },
];

export function mapModeForStatusFilter(
  status: GestionDomiciliosStatusOperativo
): GestionDomiciliosMapMode {
  switch (status) {
    case "requiere_accion":
    case "sin_punto":
    case "punto_dudoso":
    case "error":
      return "problematic";
    case "manual":
      return "manual";
    case "geolocalizado":
      return "visible";
    case "todos":
      return "visible";
    default:
      return "visible";
  }
}

export function labelGeoChip(chip: "EN_MAPA" | "SIN_COORDS"): string {
  return chip === "EN_MAPA" ? "EN MAPA" : "SIN COORDS";
}

/** Línea compacta de métricas desde ``summary`` (totales globales, no paginados). */
export function formatGestionDomiciliosSummaryLine(summary: {
  requieren_accion: number;
  sin_punto: number;
  geolocalizados: number;
}): string {
  return `${summary.requieren_accion} requieren acción · ${summary.sin_punto} sin punto · ${summary.geolocalizados} en mapa`;
}
