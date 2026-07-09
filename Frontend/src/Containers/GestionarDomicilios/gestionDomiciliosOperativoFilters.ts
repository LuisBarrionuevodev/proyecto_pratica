import type { GestionDomiciliosMapMode, GestionDomiciliosStatusOperativo } from "../../api/gestionDomiciliosApi";

export type GestionDomiciliosFiltroOption = {
  value: GestionDomiciliosStatusOperativo;
  label: string;
};

/** Filtros operativos visibles al operador (sin slices técnicos). */
export const GESTION_DOMICILIOS_FILTROS: GestionDomiciliosFiltroOption[] = [
  { value: "requiere_accion", label: "Requieren acción" },
  { value: "sin_punto", label: "Sin punto" },
  { value: "punto_dudoso", label: "Punto dudoso" },
  { value: "manual", label: "Manuales" },
  { value: "geolocalizado", label: "Geolocalizados" },
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
