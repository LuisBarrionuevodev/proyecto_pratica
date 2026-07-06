import type { DomiciliosSlice } from "./types";

export type DomicilioSliceTabConfig = {
  slice: DomiciliosSlice;
  label: string;
  /** Tooltip opcional; no altera el slice enviado al backend. */
  hint?: string;
};

/** Tabs legacy (7 slices) — filtros secundarios PR6B; queries backend intactas. */
export const DOMICILIOS_SLICE_TABS: DomicilioSliceTabConfig[] = [
  { slice: "nomenclatura_pendiente", label: "Pendientes", hint: "Calles sin normalizar en catálogo" },
  { slice: "geo_pendiente", label: "Geolocalizar", hint: "Domicilios sin punto en mapa" },
  { slice: "baja_confianza", label: "Baja confianza", hint: "Geocode con score bajo o revisión" },
  { slice: "ok", label: "Geolocalizados", hint: "Nomenclatura y geocode OK" },
  { slice: "validado_manual", label: "Manuales", hint: "Validados manualmente" },
  { slice: "error", label: "Errores", hint: "Errores de nomenclatura o geocode" },
  { slice: "all", label: "Todos", hint: "Todos los domicilios del filtro" },
];

/** Slices donde se muestra el panel de mapa / pin manual. */
export const DOMICILIOS_GEO_MAP_SLICES: ReadonlySet<DomiciliosSlice> = new Set([
  "geo_pendiente",
  "baja_confianza",
  "ok",
  "validado_manual",
  "error",
]);

export function sliceLabel(slice: DomiciliosSlice): string {
  return DOMICILIOS_SLICE_TABS.find((t) => t.slice === slice)?.label ?? slice;
}

export function sliceSupportsNomenclaturaEdit(slice: DomiciliosSlice): boolean {
  return slice === "nomenclatura_pendiente";
}

export function sliceSupportsGeoActions(slice: DomiciliosSlice): boolean {
  return DOMICILIOS_GEO_MAP_SLICES.has(slice);
}
