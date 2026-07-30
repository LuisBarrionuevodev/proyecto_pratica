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
