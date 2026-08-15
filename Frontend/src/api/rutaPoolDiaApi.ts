import { apiClient } from "./apiClient";
import type { IRutaItemMin } from "./rutasTrabajoApi";

export interface IRutaPoolDiaRow {
  pool_id: number;
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
