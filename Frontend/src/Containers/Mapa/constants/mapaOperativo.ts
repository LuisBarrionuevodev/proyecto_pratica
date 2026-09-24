/** Filtro de ejecución en mapa operativo. */
export const MAPA_EJECUCION_OPTIONS = [
  { value: "TODOS", label: "Todos" },
  { value: "REALIZADO", label: "Realizados" },
  { value: "NO_REALIZADO", label: "No realizados" },
] as const;

/** Filtro de origen operativo (``tipo_iniciador``). */
export const MAPA_ORIGEN_OPTIONS = [
  { value: "TODOS", label: "Todos" },
  { value: "RELEVAMIENTO", label: "Relevamiento" },
  { value: "DENUNCIA", label: "Denuncia" },
  { value: "REINSPECCION_NOTIFICACION", label: "Reinspección notificación" },
  { value: "OFICIO", label: "Oficio" },
] as const;

/** Filtro de motivo no realizado (solo aplica si ejecución incluye NO_REALIZADO). */
export const MAPA_MOTIVO_NO_REALIZADO_OPTIONS = [
  { value: "TODAS", label: "Todas" },
  { value: "LOCAL_CERRADO", label: "Local cerrado" },
  { value: "NO_EXISTE_LOCAL", label: "No existe local" },
  { value: "INCLEMENCIA_TIEMPO", label: "Inclemencia tiempo" },
  { value: "OTRO", label: "Otro" },
] as const;

export function mapaMotivoQueryValue(motivo: string): string | undefined {
  const v = motivo?.trim();
  if (!v || v === "TODAS") return undefined;
  return v;
}

export function mapaOrigenQueryValue(origen: string): string | undefined {
  const v = origen?.trim();
  if (!v || v === "TODOS") return undefined;
  return v;
}

export function mapaEjecucionQueryValue(ejecucion: string): string {
  const v = ejecucion?.trim();
  if (!v || v === "TODOS") return "TODOS";
  return v;
}

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
