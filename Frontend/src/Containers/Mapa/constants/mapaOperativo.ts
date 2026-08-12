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

/** Query param ``rubro_id`` para GET /map/operativo/realizados (vacío = sin filtro). */
export function mapaRealizadosRubroQueryValue(rubroId: string): number | undefined {
  const v = rubroId?.trim();
  if (!v) return undefined;
  const n = Number(v);
  return Number.isNaN(n) ? undefined : n;
}

/** Mensaje cuando el mapa no tiene puntos para los filtros activos. */
export function mapaRealizadosEmptyMessage(params: {
  tipo: string;
  rubroLabel?: string;
}): string {
  const tipoOpt = MAPA_TIPO_INICIADOR_OPTIONS.find((o) => o.value === params.tipo);
  const filtros: string[] = [];
  if (params.tipo && params.tipo !== "TODOS" && tipoOpt) {
    filtros.push(`tipo «${tipoOpt.label}»`);
  }
  if (params.rubroLabel?.trim()) {
    filtros.push(`rubro «${params.rubroLabel.trim()}»`);
  }
  if (filtros.length > 0) {
    return `No hay visitas realizadas con ${filtros.join(" y ")} en el rango de fechas. Probá «Todos» o ampliá el período.`;
  }
  return "No hay visitas realizadas en mapa para ese rango (¿geocode OK del domicilio de la actuación?).";
}
