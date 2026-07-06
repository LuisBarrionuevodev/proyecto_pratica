import type { DomiciliosSlice } from "./types";

import type { DomiciliosViewTab } from "./domicilioViewTabs";

const EMPTY_BY_VIEW: Record<DomiciliosViewTab, string> = {
  para_revisar: "No hay domicilios pendientes de revisión.",
  mapa: "No hay puntos para mostrar en el mapa.",
  validados: "No hay domicilios validados en este filtro.",
  todos: "No hay domicilios para mostrar.",
};

export function getDomicilioViewEmptyMessage(view: DomiciliosViewTab): string {
  return EMPTY_BY_VIEW[view] ?? EMPTY_BY_VIEW.todos;
}

const EMPTY_BY_SLICE: Record<DomiciliosSlice, string> = {
  nomenclatura_pendiente: "No hay domicilios pendientes de nomenclatura.",
  geo_pendiente: "No hay domicilios pendientes de geolocalización.",
  baja_confianza: "No hay domicilios para revisar por baja confianza.",
  ok: "No hay domicilios geolocalizados en este filtro.",
  validado_manual: "No hay domicilios validados manualmente.",
  error: "No hay domicilios con error.",
  all: "No hay domicilios para mostrar.",
};

export function getDomicilioSliceEmptyMessage(slice: DomiciliosSlice): string {
  return EMPTY_BY_SLICE[slice] ?? EMPTY_BY_SLICE.all;
}
