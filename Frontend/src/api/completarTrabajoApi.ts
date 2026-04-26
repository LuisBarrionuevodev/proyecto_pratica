import { apiClient } from "./apiClient";

/** Fila del listado Completar trabajo, alineada al presenter backend. */
export interface ICompletarTrabajoPendienteRow {
  id: number;
  actuacion_id: number;
  ruta_item_id: number;
  ruta_trabajo_id: number;
  ruta_grupo_id: number | null;
  iniciador_ruta_id: number;
  grupo_nombre: string | null;
  fecha_actuacion: string | null;
  tipo_iniciador: string | null;
  iniciador_estado: string | null;
  orden_trabajo_numero: string | null;
  tipo_actuacion: string | null;
  /** Tipo de catálogo coherente con `tipo_iniciador` (referencia para el formulario de tipo). */
  tipo_actuacion_esperado?: string | null;
  /** Nombres de inspectores (misma convención que grilla actuaciones). */
  inspector1?: string | null;
  inspector2?: string | null;
  inspector3?: string | null;
  /** Nombre de fantasía del comercio / local (actuación). */
  nombre_local?: string | null;
  contraproducencia: string | null;
  calle: string | null;
  numero: string | null;
  /** FK domicilio de la actuación; para edición/nomenclatura futura sin alta “desde cero”. */
  domicilio_id?: number | null;
  domicilio_texto: string | null;
  rubro_nombre: string | null;
  inspectores_texto: string | null;
  estado_operativo: string | null;
  observaciones_ejecucion: string | null;
  numero_tipo?: string | null;
  doc_nro?: string | null;
  contrib_apellido?: string | null;
  contrib_nombre?: string | null;
  razon_social?: string | null;
  acta_inspeccion_num?: string | null;
  acta_notificacion_num?: string | null;
  notificacion_motivo_1?: string | null;
  notificacion_motivo_2?: string | null;
  notificacion_motivo_3?: string | null;
  acta_comprobacion_num?: string | null;
  comprobacion_motivo?: string | null;
  acta_clausura_num?: string | null;
  acta_decomiso_num?: string | null;
  decomiso_kilos_total?: number | null;
  /** Resultado explícito reinspección por oficio (Etapa 1 backend). */
  resultado_cumplimiento_oficio?: "CUMPLE" | "NO_CUMPLE" | null;
  /** Solo en merge cliente → POST; no viene del listado. */
  inspectores?: string[];
}

export interface ICompletarTrabajoPendientesMeta {
  total: number;
  page: number;
  per_page: number;
  fecha: string;
}

export interface ICompletarTrabajoPendientesResponse {
  items: ICompletarTrabajoPendienteRow[];
  meta: ICompletarTrabajoPendientesMeta;
}

export interface IGetCompletarTrabajoPendientesParams {
  fecha: string;
  page?: number;
  per_page?: number;
}

/** Fila del GET resumen Completar trabajo (carrusel + calendario operativo). */
export interface ICompletarTrabajoPendienteDiaResumen {
  fecha: string;
  /** Ítems EN_PROCESO pendientes de cierre (mismo criterio que el grid por fecha). */
  total: number;
  atrasado: boolean;
  items_con_actuacion?: number;
  hubo_actividad?: boolean;
  sin_pendientes_cierre?: boolean;
  /** `CON_PENDIENTES` | `COMPLETO` — ausencia en `dias` = sin actividad en el módulo para esa fecha. */
  categoria_calendario?: "CON_PENDIENTES" | "COMPLETO";
}

export interface ICompletarTrabajoPendientesResumenMeta {
  fecha_desde: string;
  fecha_hasta: string;
  hoy: string;
}

export interface ICompletarTrabajoPendientesResumenResponse {
  dias: ICompletarTrabajoPendienteDiaResumen[];
  meta: ICompletarTrabajoPendientesResumenMeta;
}

export interface IGetCompletarTrabajoPendientesResumenParams {
  fecha_desde: string;
  fecha_hasta: string;
}

/**
 * Resumen agregado por día operativo de ruta (pendientes de completar), para chips / preview.
 */
export const getCompletarTrabajoPendientesResumen = async (
  params: IGetCompletarTrabajoPendientesResumenParams
): Promise<ICompletarTrabajoPendientesResumenResponse> => {
  const { data } = await apiClient.get<ICompletarTrabajoPendientesResumenResponse>(
    "/actuaciones/completar-trabajo/pendientes/resumen",
    {
      params: {
        fecha_desde: params.fecha_desde,
        fecha_hasta: params.fecha_hasta,
      },
    }
  );
  return data;
};

/** Inspectores del grupo de ruta (solo lectura en Completar trabajo). */
export interface ICompletarTrabajoInspectorGrupo {
  ruta_grupo_inspector_id: number;
  inspector_id: number;
  nombre: string | null;
  legajo: string | null;
}

export interface ICompletarTrabajoUiPolicy {
  recurso_logico: string;
  ancla_operativa: string;
  orden_trabajo_y_fecha_readonly: boolean;
  inspectores_readonly: boolean;
  previas_visible: boolean;
  post_cierre: string;
}

/** Respuesta GET detalle (fase 1) para armar el formulario. */
export interface ICompletarTrabajoDetalleResponse {
  row: ICompletarTrabajoPendienteRow;
  inspectores_grupo: ICompletarTrabajoInspectorGrupo[];
  tipo_actuacion_esperado: string | null;
  ui_policy: ICompletarTrabajoUiPolicy;
}

export const getCompletarTrabajoDetalle = async (
  rutaItemId: number
): Promise<ICompletarTrabajoDetalleResponse> => {
  const { data } = await apiClient.get<ICompletarTrabajoDetalleResponse>(
    `/actuaciones/completar-trabajo/detalle/${rutaItemId}`
  );
  return data;
};

/**
 * Trabajos pendientes de completar para una fecha (ruta publicada + ítem EN_PROCESO).
 */
export const getCompletarTrabajoPendientes = async (
  params: IGetCompletarTrabajoPendientesParams
): Promise<ICompletarTrabajoPendientesResponse> => {
  const { data } = await apiClient.get<ICompletarTrabajoPendientesResponse>(
    "/actuaciones/completar-trabajo/pendientes",
    {
      params: {
        fecha: params.fecha,
        page: params.page ?? 1,
        per_page: params.per_page ?? 20,
      },
    }
  );
  return data;
};

/** Body POST cerrar: PR2 + actas si visita realizada (sin contraproducencia). */
export interface ICompletarTrabajoCierreBody {
  tipo_actuacion?: string | null;
  contraproducencia?: string | null;
  rubro_nombre?: string | null;
  calle?: string | null;
  numero?: string | null;
  numero_tipo?: string | null;
  doc_nro?: string | null;
  contrib_apellido?: string | null;
  contrib_nombre?: string | null;
  razon_social?: string | null;
  observaciones_ejecucion?: string | null;
  acta_inspeccion_num?: string | null;
  acta_notificacion_num?: string | null;
  notificacion_motivo_1?: string | null;
  notificacion_motivo_2?: string | null;
  notificacion_motivo_3?: string | null;
  acta_comprobacion_num?: string | null;
  comprobacion_motivo?: string | null;
  acta_clausura_num?: string | null;
  acta_decomiso_num?: string | null;
  decomiso_kilos_total?: number | null;
  nombre_local?: string | null;
  inspectores?: string[] | null;
  /** Solo válido en backend para `REINSPECCION_OFICIO` y visita realizada. */
  resultado_cumplimiento_oficio?: "CUMPLE" | "NO_CUMPLE" | null;
}

export const postCompletarTrabajoCerrar = async (
  rutaItemId: number,
  body: ICompletarTrabajoCierreBody
): Promise<{ item: ICompletarTrabajoPendienteRow }> => {
  const { data } = await apiClient.post<{ item: ICompletarTrabajoPendienteRow }>(
    `/actuaciones/completar-trabajo/cerrar/${rutaItemId}`,
    body
  );
  return data;
};
