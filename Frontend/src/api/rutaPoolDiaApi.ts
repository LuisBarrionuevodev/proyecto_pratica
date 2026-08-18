import { apiClient } from "./apiClient";
import type { IIniciadorOperativoCampos, IRutaItemMin } from "./rutasTrabajoApi";

export type { IDetalleOperativoItem, IIniciadorOperativoCampos } from "./rutasTrabajoApi";

export interface IRutaPoolDiaRow extends IIniciadorOperativoCampos {  pool_id: number;
  fecha: string | null;
  turno_id?: number | null;
  estado: string;
  origen_tipo?: string | null;
  iniciador_id: number;
  iniciador_ruta_id: number;
  actuacion_id?: number | null;
  domicilio_id?: number | null;
  domicilio_texto?: string | null;
  distrito_id?: number | null;
  distrito_nombre?: string | null;
  rubro_nombre?: string | null;
  prioridad?: number | null;
  prioridad_categoria?: "BAJA" | "MEDIA" | "ALTA";
  nombre_fantasia?: string | null;
  angulo_esquina?: string | null;
  badges?: {
    tipo_label?: string | null;
    estado_label?: string | null;
    origen_label?: string | null;
    prioridad_label?: string | null;
  };
  identificadores?: {
    numero_oficio?: string | null;
    anio_oficio?: number | null;
    numero_comprobacion?: string | null;
    anio_comprobacion?: number | null;
    numero_notificacion?: string | null;
    anio_notificacion?: number | null;
    fecha_vencimiento_notificacion?: string | null;
    numero_denuncia?: string | null;
    numero_expediente?: string | null;
    anio_expediente?: string | null;
    prorroga_dias?: number | null;
    prorroga_texto?: string | null;
    causa?: string | null;
    juzgado_nombre?: string | null;
    motivo_denuncia?: string | null;
  };
  ruta_trabajo_id?: number | null;
  ruta_item_id?: number | null;
  ruta_estado?: string | null;
  puede_agregar_a_ruta?: boolean;
  motivo_bloqueo?: string | null;
}

export interface ICreateRutaPoolDiaRequest {
  origen_tipo?: string;
  iniciador_ruta_id?: number;
  iniciador_id?: number;
  actuacion_id?: number;
  fecha: string;
  turno_id?: number;
  ruta_trabajo_id?: number;
  observacion?: string;
}

export interface ICreateRutaPoolDiaResponse {
  item: IRutaPoolDiaRow;
}

export interface IListRutaPoolDiaParams {
  fecha: string;
  turno_id?: number;
  distrito_id?: number;
  rubro_id?: number;
  estado?: string;
  q?: string;
  page?: number;
  per_page?: number;
}

export interface IListRutaPoolDiaResponse {
  items: IRutaPoolDiaRow[];
  meta: { total: number; page: number; per_page: number };
}

export interface IAgregarDesdePoolRequest {
  pool_ids: number[];
  grupo_id: number;
}

export interface IAgregarDesdePoolResponse {
  items: IRutaItemMin[];
  pool_rows: IRutaPoolDiaRow[];
}

/** Alta en pool del día (`POST /ruta-pool-dia`). */
export async function createRutaPoolDia(
  payload: ICreateRutaPoolDiaRequest
): Promise<ICreateRutaPoolDiaResponse> {
  const { data } = await apiClient.post<ICreateRutaPoolDiaResponse>("/ruta-pool-dia", payload);
  return data;
}

/** Listado paginado del pool (`GET /ruta-pool-dia`). */
export async function listRutaPoolDia(params: IListRutaPoolDiaParams): Promise<IListRutaPoolDiaResponse> {
  const { data } = await apiClient.get<IListRutaPoolDiaResponse>("/ruta-pool-dia", { params });
  return data;
}

/** Asigna filas EN_POOL a un grupo de ruta BORRADOR. */
export async function agregarDesdePoolRuta(
  rutaId: number,
  payload: IAgregarDesdePoolRequest
): Promise<IAgregarDesdePoolResponse> {
  const { data } = await apiClient.post<IAgregarDesdePoolResponse>(
    `/rutas-trabajo/${rutaId}/agregar-desde-pool`,
    payload
  );
  return data;
}

/** Baja lógica de entrada del pool (`DELETE /ruta-pool-dia/:id`). */
export async function deleteRutaPoolDia(poolId: number): Promise<{ item: IRutaPoolDiaRow }> {
  const { data } = await apiClient.delete<{ item: IRutaPoolDiaRow }>(`/ruta-pool-dia/${poolId}`);
  return data;
}

/** Libera pool o ruta borrador sin OT (`POST /ruta-pool-dia/:id/liberar`). */
export async function liberarRutaPoolDia(poolId: number): Promise<{ item: IRutaPoolDiaRow }> {
  const { data } = await apiClient.post<{ item: IRutaPoolDiaRow }>(`/ruta-pool-dia/${poolId}/liberar`);
  return data;
}
