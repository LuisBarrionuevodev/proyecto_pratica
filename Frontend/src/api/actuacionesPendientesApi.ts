import { apiClient } from "./apiClient";
import type { IActuacionListItem } from "./actuacionesListApi";

export type ActuacionesPendientesTipo = "domicilios" | "sin_expediente" | "notificaciones";

export interface IActuacionesPendientesSummary {
  total: number;
  domicilios: number;
  sin_expediente: number;
  notificaciones: number;
}

export interface IActuacionesPendientesItem extends IActuacionListItem {
  /** Solo rama NOTIFICACION; vencimiento operativo desde `Notificacion.fecha_vencimiento`. */
  dias_restantes?: number | null;
  /** Solo rama NOTIFICACION; count expedientes `PRORROGA_NOTIFICACION`. */
  plazos_otorgados?: number | null;
  /** Primera visita posterior (mismo domicilio) con comprobación; rama COMPROBACION o misma actuación mixta en listado notificación: acta de la fila. */
  comprobacion_posterior_fecha?: string | null;
  comprobacion_posterior_inspectores_texto?: string | null;
  comprobacion_posterior_acta_num?: string | null;
  /** Con `source_type=notificacion` en el GET puede ser NOTIFICACION aunque la actuación tenga también comprobación (canal paralelo). */
  source_type?: "NOTIFICACION" | "COMPROBACION";
  /** FKs de contexto (bandeja expediente); útiles para normalizar canal en UI. */
  notificacion_id?: number | null;
  comprobacion_id?: number | null;
  domicilio_id?: number | null;
  numero_esquina?: string | null;
  calle_ingresada?: string | null;
  calle_normalizada?: string | null;
  esquina_normalizada?: string | null;
  esquina_catalogo_id?: number | null;
  esquina_status?: string | null;
  esquina_score?: number | null;
  calle_estado?: string | null;
  calle_score?: number | null;
  calle_sugerida?: string | null;
  calle_mostrar?: string | null;
  calle_catalogo_id?: number | null;
  esquina_catalogo_id?: number | null;
}

export interface IActuacionesPendientesFilters {
  tipo: ActuacionesPendientesTipo;
  desde?: string | null;
  hasta?: string | null;
}

export interface IActuacionesPendientesExpedienteResponse {
  items: IActuacionesPendientesItem[];
  meta: {
    total: number;
    desde: string | null;
    hasta: string | null;
    source_type?: "all" | "notificacion" | "comprobacion";
  };
}

export interface IPendientesOficioItem {
  id: number;
  fecha_actuacion: string | null;
  orden_trabajo_numero: string | null;
  tipo_actuacion?: string | null;
  acta_comprobacion_num: string | null;
  comprobacion_motivo: string | null;
  contrib_apellido?: string | null;
  contrib_nombre?: string | null;
  /** Persona jurídica; si el backend la envía, la bandeja puede mostrarla. */
  razon_social?: string | null;
  doc_nro?: string | null;
  calle: string | null;
  numero: string | null;
  rubro_nombre: string | null;
  acta_inspeccion_num?: string | null;
  inspectores_texto?: string | null;
  inspector1?: string | null;
  inspector2?: string | null;
  inspector3?: string | null;
  expediente_original_id: number | null;
  expediente_original_numero: string | null;
  expediente_original_anio: string | null;
  /** Fecha del expediente de envío (ISO día) cuando existe en BD. */
  expediente_original_fecha?: string | null;
}

export interface IPendientesOficioResponse {
  items: IPendientesOficioItem[];
  meta: {
    total: number;
    desde: string | null;
    hasta: string | null;
  };
}

export interface ICreateOficioRequest {
  numero_oficio: string;
  fecha_oficio: string;
  juzgado_id: number;
  causa?: string | null;
  numero_expediente_oficio: string;
  /** Opcional: si no se envía, el backend usa ``fecha_oficio`` (misma fecha operativa). */
  fecha_expediente_oficio?: string;
  // Compat temporal; backend lo ignora.
  anio_expediente_oficio?: number;
}

export interface ICreateOficioResponse {
  ok: boolean;
  meta: {
    actuacion_id: number;
    oficio_id: number;
    expediente_original_id: number;
    expediente_respuesta_oficio_id: number;
  };
}

export interface IJuzgadoCatalogItem {
  id: number;
  codigo: string;
  nombre: string;
}

export interface ICreateExpedienteRequest {
  expediente_numero: string;
  fecha_expediente: string;
  // Compat temporal; backend lo ignora.
  expediente_anio?: number;
  /** Obligatorio si la actuación tiene notificación y comprobación (misma fila). */
  source_type?: "NOTIFICACION" | "COMPROBACION";
  prorroga_dias?: number;
}

export interface ICreateExpedienteResponse {
  ok: boolean;
  item: IActuacionesPendientesItem;
  meta: {
    actuacion_id: number;
    expediente_id: number;
    expediente_numero: string;
    fecha_expediente?: string | null;
    expediente_anio: string;
    source_type?: "NOTIFICACION" | "COMPROBACION";
    next_state_hint?: "PENDIENTE_REINSPECCION" | "ESPERANDO_OFICIO";
    reinspeccion_due_date?: string | null;
    plazo_dias?: number | null;
    prorroga_dias?: number | null;
  };
}

export interface ISyncNotificacionesVencidasResponse {
  status: string;
  created: number;
  eligible_notificaciones: number;
  skipped_already_blocking: number;
  collisions_idempotent: number;
  elapsed_ms: number;
  started_at: string;
}

/**
 * Materializa iniciadores REINSPECCION_NOTIFICACION (mismo pipeline que CLI / scheduler).
 * No garantiza cambios en la bandeja de expedientes de plazo de la UI.
 */
export const postSyncNotificacionesVencidas = async (): Promise<ISyncNotificacionesVencidasResponse> => {
  const { data } = await apiClient.post<ISyncNotificacionesVencidasResponse>(
    "/actuaciones/pendientes/sync-notificaciones-vencidas"
  );
  return data;
};

export const getActuacionesPendientesSummary = async (
  desde?: string | null,
  hasta?: string | null
): Promise<IActuacionesPendientesSummary> => {
  const params: Record<string, string> = {};
  if (desde) params.desde = desde;
  if (hasta) params.hasta = hasta;
  const { data } = await apiClient.get<IActuacionesPendientesSummary>("/actuaciones/pendientes/summary", { params });
  return data;
};

export const getActuacionesPendientes = async (
  filters: IActuacionesPendientesFilters
): Promise<IActuacionesPendientesItem[]> => {
  const params: Record<string, string> = { tipo: filters.tipo };
  if (filters.desde) params.desde = filters.desde;
  if (filters.hasta) params.hasta = filters.hasta;
  const { data } = await apiClient.get<IActuacionesPendientesItem[]>("/actuaciones/pendientes", { params });
  return data;
};

export type IActuacionesPendientesExpedienteOpts = {
  omitirRangoFecha?: boolean;
  mes?: number;
  anio?: number;
  /** Subcadena en apellido, nombre o razón social (solo historial notificación / backend). */
  contribuyenteQ?: string | null;
  calleQ?: string | null;
  numeroNotificacion?: string | null;
  motivoQ?: string | null;
};

export const getActuacionesPendientesExpediente = async (
  desde?: string | null,
  hasta?: string | null,
  sourceType?: "all" | "notificacion" | "comprobacion",
  distritoId?: number | null,
  opts?: IActuacionesPendientesExpedienteOpts
): Promise<IActuacionesPendientesExpedienteResponse> => {
  const params: Record<string, string> = {};
  if (desde) params.desde = desde;
  if (hasta) params.hasta = hasta;
  if (sourceType) params.source_type = sourceType;
  if (distritoId != null && distritoId > 0) params.distrito_id = String(distritoId);
  if (opts?.omitirRangoFecha) params.omitir_rango_fecha = "true";
  if (opts?.mes != null && opts.mes >= 1 && opts.mes <= 12) params.mes = String(opts.mes);
  if (opts?.anio != null && opts.anio > 0) params.anio = String(opts.anio);
  const cq = opts?.contribuyenteQ?.trim();
  if (cq) params.contribuyente_q = cq;
  const calleq = opts?.calleQ?.trim();
  if (calleq) params.calle_q = calleq;
  const nn = opts?.numeroNotificacion?.trim();
  if (nn) params.numero_notificacion = nn;
  const mq = opts?.motivoQ?.trim();
  if (mq) params.motivo_q = mq;
  const { data } = await apiClient.get<IActuacionesPendientesExpedienteResponse>(
    "/actuaciones/pendientes/expediente",
    { params }
  );
  return data;
};

export const createExpedienteDesdeActuacion = async (
  actuacionId: number,
  payload: ICreateExpedienteRequest
): Promise<ICreateExpedienteResponse> => {
  const { data } = await apiClient.post<ICreateExpedienteResponse>(
    `/actuaciones/${actuacionId}/expediente`,
    payload
  );
  return data;
};

export type IActuacionesPendientesOficioOpts = {
  omitirRangoFecha?: boolean;
};

export const getActuacionesPendientesOficio = async (
  desde?: string | null,
  hasta?: string | null,
  distritoId?: number | null,
  opts?: IActuacionesPendientesOficioOpts
): Promise<IPendientesOficioResponse> => {
  const params: Record<string, string> = {};
  if (desde) params.desde = desde;
  if (hasta) params.hasta = hasta;
  if (distritoId != null && distritoId > 0) params.distrito_id = String(distritoId);
  if (opts?.omitirRangoFecha) params.omitir_rango_fecha = "true";
  const { data } = await apiClient.get<IPendientesOficioResponse>("/actuaciones/pendientes/oficio", { params });
  return data;
};

export const createOficioDesdeActuacion = async (
  actuacionId: number,
  payload: ICreateOficioRequest
): Promise<ICreateOficioResponse> => {
  const { data } = await apiClient.post<ICreateOficioResponse>(
    `/actuaciones/${actuacionId}/oficio`,
    payload
  );
  return data;
};

export const getJuzgadosCatalogo = async (): Promise<IJuzgadoCatalogItem[]> => {
  const { data } = await apiClient.get<{ items: IJuzgadoCatalogItem[] }>("/grid/catalogs/juzgados");
  return data.items ?? [];
};

/** Expediente de envío / respuesta (GET comprobación documental). */
export interface IComprobacionDocumentalExpedienteItem {
  id: number;
  numero_expediente: string;
  anio: string;
  fecha_expediente: string | null;
  tipo_expediente: string | null;
  oficio_id: number | null;
}

export interface IComprobacionDocumentalOficioItem {
  id: number;
  numero_oficio: string;
  anio: number;
  fecha_oficio: string | null;
  causa: string | null;
  juzgado_id: number | null;
  juzgado_nombre: string | null;
}

export interface IComprobacionDocumentalEdicion {
  comprobacion_usada_como_iniciador: boolean;
  puede_editar_expediente_envio: boolean;
  puede_editar_bloque_oficio: boolean;
  puede_eliminar_expediente_envio: boolean;
  puede_eliminar_bloque_oficio: boolean;
  motivos_bloqueo_expediente_envio: string[];
  motivos_bloqueo_oficio: string[];
  motivos_bloqueo_eliminar_expediente_envio: string[];
  motivos_bloqueo_eliminar_bloque_oficio: string[];
}

/** Snapshot de referencia/visita (mismo criterio que grid / detalle recorrido). */
export type IComprobacionDocumentalReferenciaActuacion = Record<string, unknown>;

export interface IComprobacionDocumentalActaComprobacion {
  numero?: string | null;
  motivo?: string | null;
}

export interface IComprobacionDocumentalResponse {
  actuacion_id: number;
  comprobacion_id: number;
  /** Fuente canónica operativa: mismo presenter que recorrido/listado. */
  referencia_actuacion?: IComprobacionDocumentalReferenciaActuacion | null;
  acta_comprobacion?: IComprobacionDocumentalActaComprobacion | null;
  expediente_envio: IComprobacionDocumentalExpedienteItem | null;
  oficio: IComprobacionDocumentalOficioItem | null;
  expediente_respuesta: IComprobacionDocumentalExpedienteItem | null;
  edicion: IComprobacionDocumentalEdicion;
}

/** GET documental operativo de comprobación (expediente envío, oficio, expediente respuesta, permisos). */
export async function fetchComprobacionDocumental(actuacionId: number): Promise<IComprobacionDocumentalResponse> {
  const { data } = await apiClient.get<IComprobacionDocumentalResponse>(
    `/actuaciones/${actuacionId}/comprobacion/documental`
  );
  return data;
}

export type IComprobacionExpedienteEnvioPatchBody = {
  numero_expediente: string;
  fecha_expediente: string;
};

/** PATCH expediente de envío (`ENVIO_ACTA`, sin oficio). */
export async function patchComprobacionExpedienteEnvio(
  actuacionId: number,
  expedienteId: number,
  body: IComprobacionExpedienteEnvioPatchBody
): Promise<{ ok: boolean; item: IComprobacionDocumentalExpedienteItem; expediente_id: number }> {
  const { data } = await apiClient.patch<{
    ok: boolean;
    item: IComprobacionDocumentalExpedienteItem;
    expediente_id: number;
  }>(`/actuaciones/${actuacionId}/comprobacion/expediente-envio/${expedienteId}`, body);
  return data;
}

/** DELETE expediente de envío (soft delete; bloqueado si hay oficio o iniciador). */
export async function deleteComprobacionExpedienteEnvio(actuacionId: number, expedienteId: number): Promise<{ ok: boolean }> {
  const { data } = await apiClient.delete<{ ok: boolean }>(
    `/actuaciones/${actuacionId}/comprobacion/expediente-envio/${expedienteId}`
  );
  return data;
}

export type IComprobacionOficioBloquePatchBody = {
  numero_oficio: string;
  fecha_oficio: string;
  juzgado_id: number;
  causa?: string | null;
  numero_expediente_respuesta: string;
  /** Opcional: el backend alinea al expediente con ``fecha_oficio``. */
  fecha_expediente_respuesta?: string;
};

/** PATCH oficio + expediente de respuesta (misma comprobación). */
export async function patchComprobacionOficioBloque(
  actuacionId: number,
  oficioId: number,
  body: IComprobacionOficioBloquePatchBody
): Promise<{
  ok: boolean;
  oficio_item: IComprobacionDocumentalOficioItem;
  expediente_respuesta_item: IComprobacionDocumentalExpedienteItem;
  oficio_id: number;
}> {
  const { data } = await apiClient.patch<{
    ok: boolean;
    oficio_item: IComprobacionDocumentalOficioItem;
    expediente_respuesta_item: IComprobacionDocumentalExpedienteItem;
    oficio_id: number;
  }>(`/actuaciones/${actuacionId}/comprobacion/oficios/${oficioId}`, body);
  return data;
}

/** DELETE oficio + expediente de respuesta (soft delete; bloqueado si iniciador). */
export async function deleteComprobacionOficioBloque(actuacionId: number, oficioId: number): Promise<{ ok: boolean }> {
  const { data } = await apiClient.delete<{ ok: boolean }>(`/actuaciones/${actuacionId}/comprobacion/oficios/${oficioId}`);
  return data;
}

/** Expediente `PRORROGA_NOTIFICACION` (detalle por actuación). */
export interface INotificacionProrrogaExpedienteItem {
  id: number;
  numero_expediente: string;
  anio: string;
  fecha_expediente: string | null;
  created_at: string | null;
  tipo_expediente: string;
  /** Días de prórroga otorgados en esta fila (persistido en expediente). */
  plazo_otorgado: number | null;
}

export interface INotificacionPlazoNotificacionResumen {
  plazo_legal_dias: number | null;
  prorroga_total_dias: number | null;
  fecha_notificacion: string | null;
  fecha_vencimiento: string | null;
}

/** Permisos de edición (GET expedientes-prorroga). */
export interface INotificacionEdicionPermisos {
  puede_editar_expediente_prorroga: boolean;
  puede_eliminar_expediente_prorroga?: boolean;
  /** True si existe `IniciadorRuta` no borrado con `notificacion_id` de esta notificación. */
  notificacion_usada_como_iniciador?: boolean;
  motivos_bloqueo_expediente: string[];
  motivos_bloqueo_eliminar_expediente?: string[];
}

export interface INotificacionProrrogaExpedientesResponse {
  actuacion_id: number;
  notificacion_id: number;
  plazos_otorgados: number;
  plazo_notificacion: INotificacionPlazoNotificacionResumen;
  items: INotificacionProrrogaExpedienteItem[];
  edicion?: INotificacionEdicionPermisos | null;
}

/**
 * Trazabilidad de expedientes de prórroga ligados a la notificación de la actuación.
 * GET `/actuaciones/:id/notificacion/expedientes-prorroga`
 */
export async function fetchNotificacionProrrogaExpedientes(
  actuacionId: number
): Promise<INotificacionProrrogaExpedientesResponse> {
  const { data } = await apiClient.get<INotificacionProrrogaExpedientesResponse>(
    `/actuaciones/${actuacionId}/notificacion/expedientes-prorroga`
  );
  return data;
}

export type INotificacionProrrogaExpedientePatchBody = {
  numero_expediente: string;
  fecha_expediente: string;
  plazo_otorgado: number;
};

/** PATCH expediente `PRORROGA_NOTIFICACION`: número, fecha y plazo otorgado; recalcula vencimiento en servidor. */
export async function patchNotificacionProrrogaExpediente(
  actuacionId: number,
  expedienteId: number,
  body: INotificacionProrrogaExpedientePatchBody
): Promise<{
  ok: boolean;
  item: INotificacionProrrogaExpedienteItem;
  expediente_id: number;
  plazo_notificacion: INotificacionPlazoNotificacionResumen;
}> {
  const { data } = await apiClient.patch<{
    ok: boolean;
    item: INotificacionProrrogaExpedienteItem;
    expediente_id: number;
    plazo_notificacion: INotificacionPlazoNotificacionResumen;
  }>(`/actuaciones/${actuacionId}/notificacion/expedientes-prorroga/${expedienteId}`, body);
  return data;
}

/** DELETE expediente `PRORROGA_NOTIFICACION` (soft delete); recalcula prórroga total y vencimiento. */
export async function deleteNotificacionProrrogaExpediente(
  actuacionId: number,
  expedienteId: number
): Promise<{
  ok: boolean;
  plazo_notificacion: INotificacionPlazoNotificacionResumen;
}> {
  const { data } = await apiClient.delete<{
    ok: boolean;
    plazo_notificacion: INotificacionPlazoNotificacionResumen;
  }>(`/actuaciones/${actuacionId}/notificacion/expedientes-prorroga/${expedienteId}`);
  return data;
}
