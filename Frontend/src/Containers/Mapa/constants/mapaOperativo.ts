/** Filtro de tipo operativo en Mapa > Realizados (alineado a Actuaciones). */
export const MAPA_TIPO_INICIADOR_OPTIONS = [
  { value: "TODOS", label: "Todos" },
  { value: "INSPECCION", label: "Inspección" },
  { value: "REINSPECCION", label: "Reinspección" },
  { value: "RATIFICACION_CLAUSURA", label: "Ratificación de clausura" },
  { value: "RATIFICACION_DECOMISO", label: "Ratificación de decomiso" },
  { value: "VERIFICAR_INFORMAR", label: "Verificar e informar" },
] as const;
export type MapaTipoIniciadorValue = (typeof MAPA_TIPO_INICIADOR_OPTIONS)[number]["value"];

/** Query param ``tipo`` para GET /map/operativo/realizados (vacío = sin filtro). */
export function mapaRealizadosTipoQueryValue(tipo: string): string | undefined {
  const v = tipo?.trim();
  if (!v || v === "TODOS") return undefined;
  return v;
}

/** Mensaje cuando el mapa no tiene puntos para los filtros activos. */
export function mapaRealizadosEmptyMessage(params: {
  tipo: string;
  definicion?: string;
}): string {
  const tipoOpt = MAPA_TIPO_INICIADOR_OPTIONS.find((o) => o.value === params.tipo);
  const defOpt = MAPA_DEFINICION_OPTIONS.find((o) => o.value === (params.definicion ?? "TODOS"));
  const filtros: string[] = [];
  if (params.tipo && params.tipo !== "TODOS" && tipoOpt) {
    filtros.push(`tipo «${tipoOpt.label}»`);
  }
  if (params.definicion && params.definicion !== "TODOS" && defOpt) {
    filtros.push(`definición «${defOpt.label}»`);
  }
  if (filtros.length > 0) {
    return `No hay visitas realizadas con ${filtros.join(" y ")} en el rango de fechas. Probá «Todos» o ampliá el período.`;
  }
  return "No hay visitas realizadas en mapa para ese rango (¿geocode OK del domicilio de la actuación?).";
}
export const MAPA_DEFINICION_OPTIONS = [
  { value: "TODOS", label: "Todos" },
  { value: "CLAUSURA", label: "Clausura" },
  { value: "DECOMISO", label: "Decomiso" },
  { value: "CLAUSURA_DECOMISO", label: "Clausura + decomiso" },
] as const;
