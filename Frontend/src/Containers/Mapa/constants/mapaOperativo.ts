/** Universo de tipo de iniciador / trabajo (pendientes y realizados). */
export const MAPA_TIPO_INICIADOR_OPTIONS = [
  { value: "TODOS", label: "Todos" },
  { value: "DENUNCIAS", label: "Denuncias" },
  { value: "REINSPECCION_OFICIO", label: "Reinspecciones por oficio" },
  { value: "RELEVAMIENTOS", label: "Relevamientos" },
  { value: "NOTIFICACION_VENCIDA", label: "Notificaciones con plazo vencido" },
] as const;

export type MapaTipoIniciadorValue = (typeof MAPA_TIPO_INICIADOR_OPTIONS)[number]["value"];

export const MAPA_DEFINICION_OPTIONS = [
  { value: "TODOS", label: "Todos" },
  { value: "CLAUSURA", label: "Clausura" },
  { value: "DECOMISO", label: "Decomiso" },
  { value: "CLAUSURA_DECOMISO", label: "Clausura + decomiso" },
] as const;
