import { apiClient } from "./apiClient";

/** Fila de `GET /establecimientos-operativos` (alineada al presenter backend). */
export interface IEstablecimientoOperativoListItem {
  id: number;
  domicilio_id: number;
  created_at: string | null;
  updated_at: string | null;
  calle: string | null;
  numero: string | null;
  calle_normalizada: string | null;
  contrib_apellido: string | null;
  contrib_nombre: string | null;
  razon_social: string | null;
  documento: string | null;
  rubro_nombre: string | null;
  distrito_id: number | null;
  distrito_nombre: string | null;
  /** Dirección operativa/normalizada para UI (detalle). */
  domicilio_texto?: string | null;
}

export interface IEstablecimientosOperativosListMeta {
  total: number;
  page: number;
  page_size: number;
}

export interface IEstablecimientosOperativosListResponse {
  items: IEstablecimientoOperativoListItem[];
  meta: IEstablecimientosOperativosListMeta;
}

export interface IEstablecimientosOperativosListFilters {
  page?: number;
  page_size?: number;
  calle?: string | null;
  contrib?: string | null;
  distrito_id?: number | null;
  rubro_id?: number | null;
}

/**
 * Listado paginado de fichas operativas (JWT vía apiClient).
 */
export async function getEstablecimientosOperativos(
  filters?: IEstablecimientosOperativosListFilters
): Promise<IEstablecimientosOperativosListResponse> {
  const params: Record<string, string> = {};
  if (filters?.page != null) params.page = String(filters.page);
  if (filters?.page_size != null) params.page_size = String(filters.page_size);
  if (filters?.calle?.trim()) params.calle = filters.calle.trim();
  if (filters?.contrib?.trim()) params.contrib = filters.contrib.trim();
  if (filters?.distrito_id != null) params.distrito_id = String(filters.distrito_id);
  if (filters?.rubro_id != null) params.rubro_id = String(filters.rubro_id);

  const { data } = await apiClient.get<IEstablecimientosOperativosListResponse>(
    "/establecimientos-operativos",
    { params }
  );
  return data;
}

/** `GET /establecimientos-operativos/:id` (misma base que listado + métricas). */
export interface IEstablecimientoOperativoDetail extends IEstablecimientoOperativoListItem {
  actuaciones_count: number;
  ultima_actuacion_fecha: string | null;
  numero_tipo?: string | null;
  esquina_raw?: string | null;
  contribuyente_id?: number | null;
  lat?: number | string | null;
  lng?: number | string | null;
  nombre_local?: string | null;
}

export interface ICorreccionContribuyenteIn {
  documento?: string | null;
  apellido?: string | null;
  nombre?: string | null;
  razon_social?: string | null;
}

export interface ICorreccionDomicilioIn {
  calle?: string | null;
  numero?: string | null;
  numero_tipo?: "NUMERO" | "ESQUINA" | "OTRO" | null;
  esquina?: string | null;
}

export interface ICorreccionLocalIn {
  rubro_nombre?: string | null;
  nombre_local?: string | null;
}

export interface ICorreccionEstablecimientoPayload {
  contribuyente?: ICorreccionContribuyenteIn;
  domicilio?: ICorreccionDomicilioIn;
  local?: ICorreccionLocalIn;
  confirmado?: boolean;
}

export interface ICorreccionIdsResumen {
  cantidad: number;
  ids: number[];
}

export interface ICorreccionConflicto {
  codigo?: string | null;
  detail?: string | null;
  domicilio_ids_ambiguos?: number[];
}

export interface ICorreccionEstablecimientoPreview {
  establecimiento_operativo_id: number;
  puede_aplicar: boolean;
  sin_cambios?: boolean;
  conflicto?: ICorreccionConflicto | null;
  advertencias: string[];
  snapshots_y_pdf?: { se_actualizan: boolean; detalle: string };
  coordenadas_y_distrito?: {
    se_recalculan: boolean;
    distrito_id?: number | null;
    lat?: number | string | null;
    lng?: number | string | null;
  };
  contribuyente?: {
    actual: Record<string, string | number | null> | null;
    propuesto: Record<string, string | number | null> | null;
    cambia: boolean;
    establecimientos_afectados: ICorreccionIdsResumen;
    actuaciones_afectadas: ICorreccionIdsResumen;
    advertencia: string;
  };
  domicilio?: {
    actual: Record<string, string | number | null>;
    actual_texto?: string | null;
    propuesto: Record<string, string | number | null>;
    cambia: boolean;
    establecimiento_seleccionado_id: number;
    domicilio_ids_ficha: number[];
    identidad_logica_completa: boolean;
    actuaciones: ICorreccionIdsResumen;
    notificaciones: ICorreccionIdsResumen;
    comprobaciones: ICorreccionIdsResumen;
    oficios: ICorreccionIdsResumen;
    iniciadores: ICorreccionIdsResumen;
    ruta_items: ICorreccionIdsResumen;
    advertencia: string;
  };
  local?: {
    actual: Record<string, string | number | null>;
    propuesto: Record<string, string | number | null> | null;
    cambia: boolean;
    establecimiento_seleccionado_id: number;
    domicilio_id?: number;
    actuaciones_que_leen_rubro?: ICorreccionIdsResumen;
    otros_establecimientos_contribuyente?: ICorreccionIdsResumen;
    reescribe_actuaciones_nombre_local?: boolean;
    advertencia: string;
  };
  applied?: boolean;
  audit_id?: number | null;
}

/**
 * Detalle de ficha operativa (404 si no existe).
 */
export async function getEstablecimientoOperativoById(
  id: number
): Promise<IEstablecimientoOperativoDetail> {
  const { data } = await apiClient.get<IEstablecimientoOperativoDetail>(
    `/establecimientos-operativos/${id}`
  );
  return data;
}

/** Bloque de acta/trámite en historial (presenter PR10.4a / establecimientos-operativos). */
export interface IHistorialActaBlock {
  numero?: string | null;
  anio?: number | null;
  texto?: string | null;
}

export interface IHistorialActasPayload {
  inspeccion?: IHistorialActaBlock | null;
  notificacion?: IHistorialActaBlock | null;
  comprobacion?: IHistorialActaBlock | null;
  clausura?: IHistorialActaBlock | null;
  decomiso?: IHistorialActaBlock | null;
}

export interface IHistorialTramitesPayload {
  expediente?: IHistorialActaBlock | null;
  oficio?: IHistorialActaBlock | null;
}

/** Fila de `GET /establecimientos-operativos/:id/actuaciones`. */
export interface IEstablecimientoOperativoHistorialRow {
  id: number;
  fecha: string | null;
  tipo_actuacion: string | null;
  contraproducencia: string | null;
  inspectores_texto?: string | null;
  domicilio_texto?: string | null;
  actas_tramites_texto?: string | null;
  actas?: IHistorialActasPayload | null;
  tramites?: IHistorialTramitesPayload | null;
}

export interface IEstablecimientoOperativoHistorialMeta {
  total: number;
  page: number;
  page_size: number;
  establecimiento_operativo_id: number;
}

export interface IEstablecimientoOperativoHistorialResponse {
  items: IEstablecimientoOperativoHistorialRow[];
  meta: IEstablecimientoOperativoHistorialMeta;
}

export interface IEstablecimientoOperativoHistorialFilters {
  page?: number;
  page_size?: number;
}

/**
 * Historial paginado de actuaciones vinculadas a la ficha.
 */
export async function getEstablecimientoOperativoActuaciones(
  establecimientoId: number,
  filters?: IEstablecimientoOperativoHistorialFilters
): Promise<IEstablecimientoOperativoHistorialResponse> {
  const params: Record<string, string> = {};
  if (filters?.page != null) params.page = String(filters.page);
  if (filters?.page_size != null) params.page_size = String(filters.page_size);

  const { data } = await apiClient.get<IEstablecimientoOperativoHistorialResponse>(
    `/establecimientos-operativos/${establecimientoId}/actuaciones`,
    { params }
  );
  return data;
}

/**
 * Vista previa del alcance de una corrección controlada (no persiste).
 */
export async function previewCorreccionEstablecimiento(
  establecimientoId: number,
  payload: ICorreccionEstablecimientoPayload
): Promise<ICorreccionEstablecimientoPreview> {
  const { data } = await apiClient.post<ICorreccionEstablecimientoPreview>(
    `/establecimientos-operativos/${establecimientoId}/correcciones/preview`,
    payload
  );
  return data;
}

/**
 * Aplica la corrección confirmada (atómica + auditoría).
 */
export async function aplicarCorreccionEstablecimiento(
  establecimientoId: number,
  payload: ICorreccionEstablecimientoPayload
): Promise<ICorreccionEstablecimientoPreview> {
  const { data } = await apiClient.post<ICorreccionEstablecimientoPreview>(
    `/establecimientos-operativos/${establecimientoId}/correcciones`,
    { ...payload, confirmado: true }
  );
  return data;
}

export interface IVinculacionEstablecimientoPayload {
  documento: string;
  fingerprint?: string | null;
  confirmado?: boolean;
}

export interface IVinculacionContribuyentePublico {
  id: number;
  documento: string | null;
  apellido: string | null;
  nombre: string | null;
  razon_social: string | null;
}

export interface IVinculacionEstablecimientoPreview {
  establecimiento_operativo_id: number;
  puede_aplicar: boolean;
  situacion: "A" | "B" | "BLOQUEO" | string;
  fingerprint: string | null;
  conflicto?: ICorreccionConflicto | null;
  advertencias: string[];
  advertencia?: string;
  snapshots_y_pdf?: { se_actualizan: boolean; detalle: string };
  coordenadas_y_distrito?: {
    se_recalculan: boolean;
    distrito_id?: number | null;
    lat?: number | string | null;
    lng?: number | string | null;
  };
  establecimiento?: {
    id: number;
    domicilio_id: number;
    domicilio_texto?: string | null;
    domicilio_ids_ficha: number[];
    identidad_logica_completa: boolean;
  };
  contribuyente_actual: IVinculacionContribuyentePublico | null;
  contribuyente_destino: IVinculacionContribuyentePublico | null;
  alcance: {
    actuaciones: ICorreccionIdsResumen;
    notificaciones: ICorreccionIdsResumen;
    comprobaciones: ICorreccionIdsResumen;
    oficios: ICorreccionIdsResumen;
    iniciadores: ICorreccionIdsResumen;
    ruta_items: ICorreccionIdsResumen;
    ruta_estados?: Array<Record<string, string | number | null>>;
  };
  otros_locales_contribuyente_anterior: ICorreccionIdsResumen;
  otros_locales_contribuyente_destino: ICorreccionIdsResumen;
  ficha_logica_destino: {
    existe: boolean;
    establecimiento_operativo_id: number | null;
  };
  edita_datos_destino: boolean;
  applied?: boolean;
  audit_id?: number | null;
  establecimiento_operativo_canonico_id?: number | null;
}

/**
 * Vista previa de vincular la ficha a un contribuyente existente (no persiste).
 */
export async function previewVinculacionEstablecimiento(
  establecimientoId: number,
  payload: IVinculacionEstablecimientoPayload
): Promise<IVinculacionEstablecimientoPreview> {
  const { data } = await apiClient.post<IVinculacionEstablecimientoPreview>(
    `/establecimientos-operativos/${establecimientoId}/vinculaciones/preview`,
    payload
  );
  return data;
}

/**
 * Aplica la vinculación confirmada (atómica + auditoría). Requiere fingerprint del preview.
 */
export async function aplicarVinculacionEstablecimiento(
  establecimientoId: number,
  payload: IVinculacionEstablecimientoPayload
): Promise<IVinculacionEstablecimientoPreview> {
  const { data } = await apiClient.post<IVinculacionEstablecimientoPreview>(
    `/establecimientos-operativos/${establecimientoId}/vinculaciones`,
    { ...payload, confirmado: true }
  );
  return data;
}
