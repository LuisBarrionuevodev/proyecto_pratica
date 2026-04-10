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

export interface IndicadoresResumenResponse {
  periodo: { desde: string; hasta: string };
  filtros: { distrito_id: number | null; inspector_id: number | null };
  actuaciones: IndicadoresActuacionesResumen;
  contraproducencias_top: IndicadoresContraproducenciaTopItem[];
  actas_por_tipo: IndicadoresActasPorTipo;
  ruta_items_ejecucion: IndicadoresRutaItemsEjecucion;
  top_rubros: IndicadoresRubroTopItem[];
  decomiso_kg: IndicadoresDecomisoKg;
}

export interface IndicadoresResumenParams {
  desde: string;
  hasta: string;
  distrito_id?: number;
  inspector_id?: number;
}

/**
 * Agregados del dashboard operativo (backend v1).
 *
 * Parámetros: rango de fechas YYYY-MM-DD; filtros opcionales.
 * Retorno: payload JSON del endpoint.
 * Errores: axios (401 redirige vía interceptor; 422 con body.errors).
 */
export const fetchIndicadoresResumen = async (
  params: IndicadoresResumenParams
): Promise<IndicadoresResumenResponse> => {
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
  const { data } = await apiClient.get<IndicadoresResumenResponse>("/api/indicadores/resumen", {
    params: query,
  });
  return data;
};
