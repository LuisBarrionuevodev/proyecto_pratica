import { apiClient } from "./apiClient";
import type { IPendientesOficioResponse } from "./actuacionesPendientesApi";

export type FetchComprobacionPendientesOficioOpts = {
  /** Igual que pendientes/expediente: sin acotar por mes cuando es true (evita filas “perdidas” fuera del mes). */
  omitirRangoFecha?: boolean;
};

/** Reutiliza el mismo contrato que la bandeja esperando oficio. */
export async function fetchComprobacionPendientesOficio(
  desde?: string | null,
  hasta?: string | null,
  distritoId?: number | null,
  opts?: FetchComprobacionPendientesOficioOpts
): Promise<IPendientesOficioResponse> {
  const params: Record<string, string> = {};
  if (desde) params.desde = desde;
  if (hasta) params.hasta = hasta;
  if (distritoId != null && distritoId > 0) params.distrito_id = String(distritoId);
  if (opts?.omitirRangoFecha) params.omitir_rango_fecha = "true";
  const { data } = await apiClient.get<IPendientesOficioResponse>("/actuaciones/pendientes/oficio", { params });
  return data;
}

export interface IReinspeccionOficioPendienteRow {
  iniciador_id: number;
  estado_iniciador: string;
  tipo_iniciador: string;
  fecha_origen_iniciador: string | null;
  id: number;
  fecha_actuacion: string | null;
  orden_trabajo_numero: string | null;
  acta_comprobacion_num: string | null;
  comprobacion_motivo: string | null;
  rubro_nombre: string | null;
  calle: string | null;
  numero: string | null;
  contrib_apellido?: string | null;
  contrib_nombre?: string | null;
  razon_social?: string | null;
  oficio_numero?: string | null;
  oficio_anio?: number | null;
  documento_pendiente: string;
  /** Snapshot alineado a `actuacion_to_grid_row` + detalle documental (presenter reinspección). */
  doc_nro?: string | null;
  acta_inspeccion_num?: string | null;
  inspectores_texto?: string | null;
  inspector1?: string | null;
  inspector2?: string | null;
  inspector3?: string | null;
  tipo_actuacion?: string | null;
  oficio_causa?: string | null;
  fecha_oficio?: string | null;
  juzgado_nombre?: string | null;
  expediente_numero?: string | null;
  expediente_anio?: number | null;
  expediente_envio_numero?: string | null;
  expediente_envio_anio?: string | number | null;
  fecha_expediente_envio?: string | null;
  expediente_respuesta_numero?: string | null;
  expediente_respuesta_anio?: string | number | null;
  fecha_expediente_respuesta?: string | null;
  /** Misma lógica que Recorrido: tipo de visita desambigüado (ratificación / verificar e informar) o ausente. */
  tipo_visita_resultado?: string | null;
  /** Etiqueta de circuito documental (misma fuente que la tabla Recorrido). */
  estado_recorrido?: string | null;
  /** FK del oficio de la fila (PR4b: una fila por oficio/iniciador). */
  oficio_id?: number | null;
  /** Clave estable para tablas con varias filas por actuación. */
  bandeja_row_key?: string | null;
  /** STAB-3: policy por oficio (presenter reinspección). */
  editable?: boolean;
  bloqueado_motivo?: string | null;
  ruta_estado?: string | null;
  estado_ejecucion?: string | null;
  en_ruta_borrador?: boolean;
  estado_operativo?: string | null;
  acciones_permitidas?: string[];
}

export interface IReinspeccionOficioResponse {
  items: IReinspeccionOficioPendienteRow[];
  meta: { total: number; desde: string | null; hasta: string | null };
}

export type FetchPendientesReinspeccionOficioOpts = {
  /** Sin acotar por mes (evita filas fuera del mes corriente; mismo criterio que pendientes/oficio). */
  omitirRangoFecha?: boolean;
};

export async function fetchPendientesReinspeccionOficio(
  desde?: string | null,
  hasta?: string | null,
  distritoId?: number | null,
  opts?: FetchPendientesReinspeccionOficioOpts
): Promise<IReinspeccionOficioResponse> {
  const params: Record<string, string> = {};
  if (desde) params.desde = desde;
  if (hasta) params.hasta = hasta;
  if (distritoId != null && distritoId > 0) params.distrito_id = String(distritoId);
  if (opts?.omitirRangoFecha) params.omitir_rango_fecha = "true";
  const { data } = await apiClient.get<IReinspeccionOficioResponse>(
    "/actuaciones/comprobacion/pendientes-reinspeccion-oficio",
    { params }
  );
  return data;
}

export interface IComprobacionRecorridoRow {
  id: number;
  estado_recorrido: string;
  fecha_actuacion: string | null;
  orden_trabajo_numero: string | null;
  acta_comprobacion_num: string | null;
  comprobacion_motivo: string | null;
  rubro_nombre: string | null;
  calle: string | null;
  numero: string | null;
  contrib_apellido?: string | null;
  contrib_nombre?: string | null;
  /** Misma semántica que `actuacion_to_grid_row` (persona jurídica). */
  razon_social?: string | null;
  doc_nro?: string | null;
  tipo_actuacion?: string | null;
  inspector1?: string | null;
  inspector2?: string | null;
  inspector3?: string | null;
  inspectores_texto?: string | null;
  acta_inspeccion_num?: string | null;
  expediente_numero?: string | null;
  expediente_anio?: number | null;
  oficio_numero?: string | null;
  oficio_anio?: number | null;
  /** Expediente de respuesta vinculado al oficio (misma semántica que pendientes de reinspección). */
  expediente_respuesta_numero?: string | null;
  expediente_respuesta_anio?: number | string | null;
  [key: string]: unknown;
}

export interface IComprobacionRecorridoListResponse {
  items: IComprobacionRecorridoRow[];
  meta: { total: number; desde: string | null; hasta: string | null };
}

export interface IComprobacionRecorridoListParams {
  desde?: string | null;
  hasta?: string | null;
  /** Si se envían ambos, el backend fija el rango al mes (prioridad sobre desde/hasta sueltos). */
  mes?: number | null;
  anio?: number | null;
  distrito_id?: number | null;
  contrib_q?: string | null;
  calle_q?: string | null;
  numero_q?: string | null;
  acta_comprobacion?: string | null;
  expediente_numero?: string | null;
  oficio_numero?: string | null;
  estado_recorrido?: string | null;
  /** CUMPLE / NO_CUMPLE (resultado_cumplimiento_oficio) */
  tipo_final?: string | null;
}

export async function fetchComprobacionRecorrido(
  paramsIn: IComprobacionRecorridoListParams = {}
): Promise<IComprobacionRecorridoListResponse> {
  const params: Record<string, string> = {};
  const p = paramsIn;
  if (p.desde) params.desde = p.desde;
  if (p.hasta) params.hasta = p.hasta;
  if (p.mes != null && p.mes > 0) params.mes = String(p.mes);
  if (p.anio != null && p.anio > 0) params.anio = String(p.anio);
  if (p.distrito_id != null && p.distrito_id > 0) params.distrito_id = String(p.distrito_id);
  if (p.contrib_q) params.contrib_q = p.contrib_q;
  if (p.calle_q) params.calle_q = p.calle_q;
  if (p.numero_q) params.numero_q = p.numero_q;
  if (p.acta_comprobacion) params.acta_comprobacion = p.acta_comprobacion;
  if (p.expediente_numero) params.expediente_numero = p.expediente_numero;
  if (p.oficio_numero) params.oficio_numero = p.oficio_numero;
  if (p.estado_recorrido) params.estado_recorrido = p.estado_recorrido;
  if (p.tipo_final) params.tipo_final = p.tipo_final;
  const { data } = await apiClient.get<IComprobacionRecorridoListResponse>("/actuaciones/comprobacion/recorrido", {
    params,
  });
  return data;
}

/** Iniciador preferente para origen del circuito (API recorrido detalle). */
export interface IComprobacionRecorridoOrigenIniciador {
  tipo_iniciador: string;
  estado_iniciador: string;
  fecha_origen: string | null;
}

/** Snapshot de la actuación (misma fuente que el grid); el modal no depende solo del listado. */
export interface IComprobacionRecorridoReferenciaActuacion {
  fecha_actuacion?: string | null;
  orden_trabajo_numero?: string | null;
  calle?: string | null;
  numero?: string | null;
  contrib_apellido?: string | null;
  contrib_nombre?: string | null;
  razon_social?: string | null;
  doc_nro?: string | null;
  rubro_nombre?: string | null;
  /** Motivo de la comprobación (misma fuente que la grilla). */
  comprobacion_motivo?: string | null;
  acta_inspeccion_num?: string | null;
  acta_comprobacion_num?: string | null;
  inspectores_texto?: string | null;
  inspector1?: string | null;
  inspector2?: string | null;
  inspector3?: string | null;
  tipo_actuacion?: string | null;
}

export interface IComprobacionRecorridoOrigen {
  descripcion?: string;
  fecha_actuacion?: string | null;
  orden_trabajo_numero?: string | null;
  iniciador?: IComprobacionRecorridoOrigenIniciador | null;
}

export interface IComprobacionRecorridoOficio {
  id?: number;
  numero_oficio?: string | null;
  anio?: number | null;
  fecha_oficio?: string | null;
  causa?: string | null;
  juzgado_id?: number | null;
  juzgado_nombre?: string | null;
}

export interface IComprobacionRecorridoResultadoFinal {
  resultado_cumplimiento_oficio?: string | null;
  estado_recorrido?: string | null;
  tipo_actuacion?: string | null;
  /** Tipo de visita desambigüado (ratificación / verificar e informar) cuando aplica oficio; preferir en UI sobre `tipo_actuacion`. */
  tipo_visita?: string | null;
}

export interface IComprobacionRecorridoDetalle {
  actuacion_id: number;
  origen: IComprobacionRecorridoOrigen;
  acta_comprobacion: Record<string, unknown>;
  expediente_comprobacion_envio: Record<string, unknown> | null;
  oficio: IComprobacionRecorridoOficio | null;
  expediente_respuesta_oficio: Record<string, unknown> | null;
  reinspeccion_por_oficio: Record<string, unknown> | null;
  resultado_final: IComprobacionRecorridoResultadoFinal;
  /** Presente desde API actual: datos de visita alineados al grid (priorizar sobre `listRow`). */
  referencia_actuacion?: IComprobacionRecorridoReferenciaActuacion | null;
}

export async function fetchComprobacionRecorridoDetalle(
  actuacionId: number
): Promise<IComprobacionRecorridoDetalle> {
  const { data } = await apiClient.get<IComprobacionRecorridoDetalle>(
    `/actuaciones/comprobacion/recorrido/${actuacionId}`
  );
  return data;
}
