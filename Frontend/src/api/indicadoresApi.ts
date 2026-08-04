import { apiClient } from "./apiClient";

export interface IndicadoresContraproducenciaTopItem {
  valor: string;
  count: number;
}

export interface IndicadoresActuacionesResumen {
  total: number;
  con_contraproducencia: number;
  sin_contraproducencia: number;
}

export interface IndicadoresActasPorTipo {
  inspeccion: number;
  notificacion: number;
  comprobacion: number;
  clausura: number;
  decomiso: number;
}

export interface IndicadoresRutaItemsEjecucion {
  total: number;
  estado_ejecucion_realizado: number;
  estado_ejecucion_no_realizado: number;
  estado_ejecucion_sin_clasificar: number;
}

/** Conteos alineados al mapa operativo D1 (misma semántica que GeoJSON pendientes/realizados). */
export interface IndicadoresMapaOperativo {
  pendientes_cola: number;
  pendientes_completar_trabajo: number;
  pendientes_total: number;
  realizados_visita: number;
}

export interface IndicadoresRubroTopItem {
  rubro_id: number;
  nombre: string;
  count: number;
}

export interface IndicadoresDecomisoKgPorMes {
  anio: number;
  mes: number;
  kg: number;
}

export interface IndicadoresDecomisoKg {
  total_kg: number;
  por_mes: IndicadoresDecomisoKgPorMes[];
}

export interface IndicadoresActasLabradasMes {
  anio: number;
  mes: number;
  total: number;
  inspeccion: number;
  notificacion: number;
  comprobacion: number;
  clausura: number;
  decomiso: number;
}

export interface IndicadoresRankingInspector {
  inspector_id: number;
  inspector_nombre: string;
  total_actuaciones: number;
}

export interface IndicadoresReinspeccionesRealizadas {
  notificacion: number;
  oficio: number;
}

export interface IndicadoresContraproducenciaPorTipo {
  valor: string;
  count: number;
}

export interface IndicadoresActuacionPorTipoOperativo {
  tipo: string;
  count: number;
}

export interface IndicadoresResumenResponse {
  periodo: { desde: string; hasta: string };
  filtros: { distrito_id: number | null; inspector_id: number | null };
  actuaciones: IndicadoresActuacionesResumen;
  contraproducencias_top: IndicadoresContraproducenciaTopItem[];
  actas_por_tipo: IndicadoresActasPorTipo;
  actas_labradas_mensual: IndicadoresActasLabradasMes[];
  ranking_inspectores: IndicadoresRankingInspector[];
  reinspecciones_realizadas: IndicadoresReinspeccionesRealizadas;
  contraproducencias_por_tipo: IndicadoresContraproducenciaPorTipo[];
  actuaciones_por_tipo_operativo: IndicadoresActuacionPorTipoOperativo[];
  ruta_items_ejecucion: IndicadoresRutaItemsEjecucion;
  mapa_operativo: IndicadoresMapaOperativo;
  top_rubros: IndicadoresRubroTopItem[];
  decomiso_kg: IndicadoresDecomisoKg;
}

/** Query params compartidos por bloques del dashboard (desde/hasta + filtros opcionales). */
export interface IndicadoresFiltrosParams {
  desde: string;
  hasta: string;
  distrito_id?: number;
  inspector_id?: number;
}

export type IndicadoresResumenParams = IndicadoresFiltrosParams;

export interface IndicadoresEjecutivoKpis {
  actuaciones_realizadas: number;
  actas_labradas: number;
  reinspecciones_notificacion_realizadas: number;
  reinspecciones_oficio_realizadas: number;
  ratificaciones_clausura_realizadas: number;
  ratificaciones_decomiso_realizadas: number;
  verificar_informar_realizadas: number;
  mercaderia_decomisada_kg: number;
}

export interface IndicadoresEjecutivoResponse {
  periodo: { desde: string; hasta: string };
  kpis: IndicadoresEjecutivoKpis;
  actas_por_tipo: IndicadoresActasPorTipo;
}

export interface IndicadoresPendientesKpis {
  relevamientos_pendientes: number;
  reinspecciones_oficio_pendientes: number;
  reinspecciones_notificacion_pendientes: number;
  denuncias_pendientes: number;
  pendientes_geolocalizacion: number;
}

export interface IndicadoresDistritoPendientesItem {
  distrito_id: number;
  distrito_codigo: string;
  distrito_nombre: string;
  relevamientos: number;
  denuncias: number;
  reinspecciones_oficio: number;
  reinspecciones_notificacion: number;
  sin_geolocalizacion: number;
  total: number;
}

export interface IndicadoresPendientesResponse {
  kpis: IndicadoresPendientesKpis;
  distritos_con_mas_pendientes: IndicadoresDistritoPendientesItem[];
}

export interface IndicadoresRubroCantidadItem {
  rubro: string;
  cantidad: number;
}

export interface IndicadoresMotivoCantidadItem {
  motivo: string;
  cantidad: number;
}

export interface IndicadoresDecomisoKgRubroItem {
  rubro: string;
  kg: number;
}

export interface IndicadoresRiesgoResponse {
  top_rubros: IndicadoresRubroCantidadItem[];
  top_motivos_notificacion: IndicadoresMotivoCantidadItem[];
  top_motivos_comprobacion: IndicadoresMotivoCantidadItem[];
  decomiso_kg_por_rubro: IndicadoresDecomisoKgRubroItem[];
}

export interface IndicadoresNoRealizadasPorTipo {
  inspeccion: number;
  reinspeccion_oficio: number;
  reinspeccion_notificacion: number;
  denuncia: number;
}

export interface IndicadoresContraproducenciaCantidadItem {
  contraproducencia: string;
  cantidad: number;
}

export interface IndicadoresDistritoNoRealizadasItem {
  distrito_id: number;
  distrito_codigo: string;
  distrito_nombre: string;
  cantidad: number;
}

export interface IndicadoresNoRealizadasResponse {
  por_tipo: IndicadoresNoRealizadasPorTipo;
  top_contraproducencias: IndicadoresContraproducenciaCantidadItem[];
  distritos_con_mas_no_realizadas: IndicadoresDistritoNoRealizadasItem[];
}

export interface IndicadorInspectorRealizadas {
  inspector_id: number;
  inspector: string;
  total_realizadas: number;
  inspecciones: number;
  reinspecciones_oficio: number;
  reinspecciones_notificacion: number;
  denuncias: number;
  tipo_principal: string;
}

export interface IndicadorInspectorNoRealizadas {
  inspector_id: number;
  inspector: string;
  total_no_realizadas: number;
  contraproducencia_principal: string;
  inspecciones: number;
  reinspecciones_oficio: number;
  reinspecciones_notificacion: number;
  denuncias: number;
}

export interface IndicadorActasPorInspector {
  inspector_id: number;
  inspector: string;
  notificacion: number;
  comprobacion: number;
  clausura: number;
  decomiso: number;
  total_actas: number;
}

export interface IndicadoresProductividadResponse {
  inspectores_realizadas: IndicadorInspectorRealizadas[];
  inspectores_no_realizadas: IndicadorInspectorNoRealizadas[];
  actas_por_inspector: IndicadorActasPorInspector[];
}

/**
 * Agregados del dashboard operativo (backend v1).
 *
 * Parámetros: rango de fechas YYYY-MM-DD; filtros opcionales.
 * Retorno: payload JSON del endpoint.
 * Errores: axios (401 redirige vía interceptor; 422 con body.errors).
 */
function buildIndicadoresQuery(params: IndicadoresFiltrosParams): Record<string, string> {
  const query: Record<string, string> = {
    desde: params.desde,
    hasta: params.hasta,
  };
  if (params.distrito_id != null) {
    query.distrito_id = String(params.distrito_id);
  }
  if (params.inspector_id != null) {
    query.inspector_id = String(params.inspector_id);
  }
  return query;
}

/**
 * Bloque ejecutivo del dashboard (visitas realizadas + actas labradas).
 *
 * Parámetros: rango YYYY-MM-DD; filtros opcionales distrito/inspector.
 * Retorno: KPIs y actas por tipo desde cierres de ruta / actuaciones del periodo.
 */
export const fetchIndicadoresEjecutivo = async (
  params: IndicadoresFiltrosParams
): Promise<IndicadoresEjecutivoResponse> => {
  const { data } = await apiClient.get<IndicadoresEjecutivoResponse>("/api/indicadores/ejecutivo", {
    params: buildIndicadoresQuery(params),
  });
  return data;
};

/**
 * Bloque operativo / pendientes (cola planificable por tipo de iniciador).
 *
 * Parámetros: rango sobre fecha_origen del iniciador; filtros opcionales.
 * Retorno: KPIs por tipo y tabla por distrito (puede venir vacía).
 */
export const fetchIndicadoresPendientes = async (
  params: IndicadoresFiltrosParams
): Promise<IndicadoresPendientesResponse> => {
  const { data } = await apiClient.get<IndicadoresPendientesResponse>("/api/indicadores/pendientes", {
    params: buildIndicadoresQuery(params),
  });
  return data;
};

/**
 * Bloque riesgo bromatológico: rubros, motivos y kg decomisados por rubro.
 */
export const fetchIndicadoresRiesgo = async (
  params: IndicadoresFiltrosParams
): Promise<IndicadoresRiesgoResponse> => {
  const { data } = await apiClient.get<IndicadoresRiesgoResponse>("/api/indicadores/riesgo", {
    params: buildIndicadoresQuery(params),
  });
  return data;
};

/**
 * Bloque no realizadas: desglose por tipo, motivos y distritos (cierres no concretados).
 */
export const fetchIndicadoresNoRealizadas = async (
  params: IndicadoresFiltrosParams
): Promise<IndicadoresNoRealizadasResponse> => {
  const { data } = await apiClient.get<IndicadoresNoRealizadasResponse>(
    "/api/indicadores/no-realizadas",
    {
      params: buildIndicadoresQuery(params),
    }
  );
  return data;
};

/**
 * Bloque productividad: realizadas, no realizadas y actas labradas por inspector.
 */
export const fetchIndicadoresProductividad = async (
  params: IndicadoresFiltrosParams
): Promise<IndicadoresProductividadResponse> => {
  const { data } = await apiClient.get<IndicadoresProductividadResponse>(
    "/api/indicadores/productividad",
    {
      params: buildIndicadoresQuery(params),
    }
  );
  return data;
};

export const fetchIndicadoresResumen = async (
  params: IndicadoresResumenParams
): Promise<IndicadoresResumenResponse> => {
  const { data } = await apiClient.get<IndicadoresResumenResponse>("/api/indicadores/resumen", {
    params: buildIndicadoresQuery(params),
  });
  return data;
};
