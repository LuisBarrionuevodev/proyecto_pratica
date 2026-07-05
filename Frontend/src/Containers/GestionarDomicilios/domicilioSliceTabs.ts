import type { DomiciliosSlice } from "./types";

export type DomicilioSliceTabConfig = {
  slice: DomiciliosSlice;
  label: string;
};

/** Tabs de Gestión Domicilios (PR3) — mapeo 1:1 con query ``slice=`` del backend. */
export const DOMICILIOS_SLICE_TABS: DomicilioSliceTabConfig[] = [
  { slice: "nomenclatura_pendiente", label: "Pendientes nomenclatura" },
  { slice: "geo_pendiente", label: "Pendientes geolocalizar" },
  { slice: "baja_confianza", label: "Baja confianza" },
  { slice: "ok", label: "Geolocalizados" },
  { slice: "validado_manual", label: "Validados manualmente" },
  { slice: "error", label: "Errores" },
  { slice: "all", label: "Todos" },
];

/** Slices donde se muestra el panel de mapa / pin manual. */
export const DOMICILIOS_GEO_MAP_SLICES: ReadonlySet<DomiciliosSlice> = new Set([
  "geo_pendiente",
  "baja_confianza",
  "ok",
  "validado_manual",
  "error",
]);

export function sliceSupportsNomenclaturaEdit(slice: DomiciliosSlice): boolean {
  return slice === "nomenclatura_pendiente";
}

export function sliceSupportsGeoActions(slice: DomiciliosSlice): boolean {
  return DOMICILIOS_GEO_MAP_SLICES.has(slice);
}
