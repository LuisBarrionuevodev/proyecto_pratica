import type { DomiciliosSlice } from "./types";

/** Tabs visibles PR6B — agrupan slices internos sin cambiar queries backend. */
export type DomiciliosViewTab = "para_revisar" | "mapa" | "validados" | "todos";

export type DomicilioViewTabConfig = {
  view: DomiciliosViewTab;
  label: string;
  hint?: string;
};

export const DOMICILIOS_VIEW_TABS: DomicilioViewTabConfig[] = [
  {
    view: "para_revisar",
    label: "Para revisar",
    hint: "Nomenclatura, geocode, baja confianza y errores",
  },
  { view: "mapa", label: "Mapa", hint: "Vista operativa tipo My Maps" },
  { view: "validados", label: "Validados", hint: "Geolocalizados y validados manualmente" },
  { view: "todos", label: "Todos", hint: "Todos los domicilios del filtro" },
];

/** Slices backend que alimenta cada tab visible. */
export const SLICES_FOR_VIEW: Record<DomiciliosViewTab, readonly DomiciliosSlice[]> = {
  para_revisar: ["nomenclatura_pendiente", "geo_pendiente", "baja_confianza", "error"],
  mapa: ["geo_pendiente", "baja_confianza", "error"],
  validados: ["ok", "validado_manual"],
  todos: ["all"],
};

/** Filtros secundarios (legacy) disponibles por tab. */
export const SECONDARY_FILTERS_FOR_VIEW: Record<
  DomiciliosViewTab,
  readonly (DomiciliosSlice | "all")[]
> = {
  para_revisar: [
    "all",
    "nomenclatura_pendiente",
    "geo_pendiente",
    "baja_confianza",
    "error",
  ],
  mapa: ["all", "geo_pendiente", "baja_confianza", "error"],
  validados: ["all", "ok", "validado_manual"],
  todos: ["all"],
};

export function viewIncludesSlice(view: DomiciliosViewTab, slice: DomiciliosSlice): boolean {
  return SLICES_FOR_VIEW[view].includes(slice);
}
