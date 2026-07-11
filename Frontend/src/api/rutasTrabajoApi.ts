import { apiClient } from "./apiClient";

export type RutaTurno = "MANIANA" | "TARDE";

export interface IRutaTrabajo {
  id: number;
  fecha: string;
  turno: RutaTurno;
  estado_ruta: string;
  numero: number;
  display_name?: string;
  observaciones: string | null;
  created_by_user_id: number;
  created_at: string | null;
  updated_at: string | null;
}

export interface IRutaGrupoInspector {
  id: number;
  inspector_id: number;
  inspector_nombre: string | null;
  inspector_legajo: string | null;
}

export interface IRutaGrupoMin {
  id: number;
  ruta_trabajo_id: number;
  nombre: string;
  estado: string | null;
  inspectores: IRutaGrupoInspector[];
  items?: IRutaItemMin[];
  created_by_user_id: number;
  created_at: string | null;
  updated_at: string | null;
}

export interface ICreateRutaTrabajoRequest {
  fecha: string;
  turno: RutaTurno;
  observaciones?: string | null;
}

export interface ICreateRutaTrabajoResponse {
  item: IRutaTrabajo;
}

export interface ICreateRutaGrupoRequest {
  nombre?: string;
  estado?: string | null;
}

export interface ICreateRutaGrupoResponse {
  item: IRutaGrupoMin;
}

export interface IReplaceGrupoInspectoresRequest {
  inspector_ids: number[];
}

export interface IReplaceGrupoInspectoresResponse {
  items: IRutaGrupoInspector[];
}

export interface IGetRutaTrabajoDetailResponse {
  ruta: IRutaTrabajo;
  grupos: IRutaGrupoMin[];
}

export interface IRutaIniciadorPendienteRow {
  id: number;
  tipo_iniciador: string;
  estado_iniciador: string;
  fecha_origen: string | null;
  prioridad: number | null;
  turno_sugerido: string | null;
  domicilio: {
    id: number | null;
    calle: string | null;
    numero: string | null;
    distrito_id: number | null;
    distrito_nombre?: string | null;
    barrio_id: number | null;
    rubro?: string | null;
  };
  origen: {
    tipo: string | null;
    denuncia_id: number | null;
    relevamiento_id: number | null;
    notificacion_id: number | null;
    oficio_id: number | null;
    actuacion_id: number | null;
  };
  observaciones: string | null;
  domicilio_texto?: string | null;
  distrito_id?: number | null;
  distrito_nombre?: string | null;
  rubro_nombre?: string | null;
  /** Discriminadores operativos del relevamiento origen (PR7.8/7.9). */
  nombre_fantasia?: string | null;
  angulo_esquina?: string | null;
  badges?: {
    tipo_label?: string | null;
    estado_label?: string | null;
    origen_label?: string | null;
    prioridad_label?: string | null;
  };
  /** Presente en respuestas de planificación / presenter extendido. */
  prioridad_categoria?: "BAJA" | "MEDIA" | "ALTA";
  elegible_urgente?: boolean;
  /** Geocodificación del domicilio (planificación / listados con joined geocode). */
  lat?: number | null;
  lng?: number | null;
  geo_status?: string | null;
  /** Números operativos para cards (STAB-10c). */
  identificadores?: {
    numero_oficio?: string | null;
    anio_oficio?: number | null;
    numero_comprobacion?: string | null;
    anio_comprobacion?: number | null;
    numero_notificacion?: string | null;
    anio_notificacion?: number | null;
    fecha_vencimiento_notificacion?: string | null;
    numero_denuncia?: string | null;
  };
}

export interface IGetRutaIniciadoresPendientesResponse {
  items: IRutaIniciadorPendienteRow[];
  meta: {
    total: number;
    page: number;
    per_page: number;
  };
}

export interface IGetRutaIniciadoresPendientesParams {
  tipo?: string;
  prioridad?: number;
  /** BAJA (=1), MEDIA (=2), ALTA (>=3); preferido frente a `prioridad` numérica. */
  prioridad_categoria?: "BAJA" | "MEDIA" | "ALTA";
  distrito?: number;
  /** Filtro por `domicilio.calle_catalogo_id` (misma noción que nomenclatura). */
  calle_catalogo_id?: number;
  q?: string;
  turno_sugerido?: "MANIANA" | "TARDE";
  page?: number;
  per_page?: number;
}

export interface IRutaItemMin {
  id: number;
  ruta_trabajo_id: number;
  ruta_grupo_id: number;
  iniciador_ruta_id: number;
  /** Tipo del iniciador vinculado (detail/assign/move/publicar). Fuente de verdad para mapa sin depender del pool. */
  tipo_iniciador?: string | null;
  /** Presente tras publicar la ruta (actuación mínima vinculada). */
  actuacion_id?: number | null;
  orden_trabajo_id?: number | null;
  orden_trabajo?: {
    id: number;
    numero_acta: string;
    anio: number;
    mes: number;
  } | null;
  estado_ruta_item: string;
  deleted_at: string | null;
  /** Detalle / mapa: desde iniciador → domicilio → geocode */
  domicilio_id?: number | null;
  domicilio_texto?: string | null;
  lat?: number | null;
  lng?: number | null;
  geo_status?: string | null;
  distrito_id?: number | null;
  distrito_nombre?: string | null;
  rubro_nombre?: string | null;
  /** Discriminadores operativos del relevamiento origen (ítem en ruta publicada/asignada). */
  nombre_fantasia?: string | null;
  angulo_esquina?: string | null;
}

export interface IAssignItemsRequest {
  iniciador_ids: number[];
}

export interface IAssignItemsResponse {
  items: IRutaItemMin[];
}

export interface IMoveItemRequest {
  target_grupo_id: number;
}

export interface IMoveItemResponse {
  item: IRutaItemMin;
}

export interface IDeleteItemResponse {
  ok: boolean;
  item_id: number;
}

export interface IDeleteGrupoResponse {
  ok: boolean;
  grupo_id: number;
  items_soft_deleted: number;
}

export interface IPatchItemOtRequest {
  numero_orden_trabajo: string;
}

export interface IPatchItemOtResponse {
  item: IRutaItemMin;
}

export interface IPublicarRutaTrabajoResponse {
  ruta: IRutaTrabajo;
  items: IRutaItemMin[];
}

export const createRutaTrabajo = async (
  payload: ICreateRutaTrabajoRequest
): Promise<ICreateRutaTrabajoResponse> => {
  const { data } = await apiClient.post<ICreateRutaTrabajoResponse>("/rutas-trabajo", payload);
  return data;
};

export const getRutaTrabajoDetail = async (rutaId: number): Promise<IGetRutaTrabajoDetailResponse> => {
  const { data } = await apiClient.get<IGetRutaTrabajoDetailResponse>(`/rutas-trabajo/${rutaId}`);
  return data;
};

/** Meta de `GET /rutas-trabajo` (borradores por defecto o `estado_ruta` explícito). */
export interface IListRutasTrabajoMeta {
  total: number;
  page: number;
  per_page: number;
  estados?: string[];
  fecha?: string | null;
  fecha_desde?: string | null;
  fecha_hasta?: string | null;
}

export interface IListRutasTrabajoResponse {
  items: IRutaTrabajo[];
  meta: IListRutasTrabajoMeta;
}

/** Sin `estado_ruta`: solo BORRADOR (comportamiento backend por defecto). */
export interface IListRutasBorradorParams {
  page?: number;
  per_page?: number;
  fecha?: string;
  fecha_desde?: string;
  fecha_hasta?: string;
}

export interface IListRutasTrabajoParams extends IListRutasBorradorParams {
  /** Uno o varios separados por coma, p. ej. `PUBLICADA` o `PUBLICADA,EN_CURSO`. */
  estado_ruta?: string;
}

export type IListRutasBorradorResponse = IListRutasTrabajoResponse;

export const listRutasBorrador = async (
  params?: IListRutasBorradorParams
): Promise<IListRutasBorradorResponse> => {
  const { data } = await apiClient.get<IListRutasTrabajoResponse>("/rutas-trabajo", { params });
  return data;
};

/**
 * Lista rutas de trabajo (`GET /rutas-trabajo`).
 * Sin `estado_ruta` el backend devuelve solo BORRADOR; con `estado_ruta=PUBLICADA` (y opcional `fecha=YYYY-MM-DD`) rutas publicadas / histórico.
 */
export const listRutasTrabajo = async (
  params?: IListRutasTrabajoParams
): Promise<IListRutasTrabajoResponse> => {
  const { data } = await apiClient.get<IListRutasTrabajoResponse>("/rutas-trabajo", { params });
  return data;
};

export const createRutaGrupo = async (
  rutaId: number,
  payload: ICreateRutaGrupoRequest
): Promise<ICreateRutaGrupoResponse> => {
  const { data } = await apiClient.post<ICreateRutaGrupoResponse>(`/rutas-trabajo/${rutaId}/grupos`, payload);
  return data;
};

export const replaceRutaGrupoInspectores = async (
  rutaId: number,
  grupoId: number,
  payload: IReplaceGrupoInspectoresRequest
): Promise<IReplaceGrupoInspectoresResponse> => {
  const path = `/rutas-trabajo/${rutaId}/grupos/${grupoId}/inspectores`;
  try {
    const { data } = await apiClient.put<IReplaceGrupoInspectoresResponse>(path, payload);
    return data;
  } catch (err: any) {
    const status = err?.response?.status;
    const body = err?.response?.data;
    // Trazabilidad mínima para diagnóstico de incidencias de asignación.
    // eslint-disable-next-line no-console
    console.error("[rutas-trabajo] replace inspectores failed", {
      method: "PUT",
      path,
      rutaId,
      grupoId,
      status,
      body,
    });
    throw err;
  }
};

export const getRutaIniciadoresPendientes = async (
  rutaId: number,
  params: IGetRutaIniciadoresPendientesParams
): Promise<IGetRutaIniciadoresPendientesResponse> => {
  const { data } = await apiClient.get<IGetRutaIniciadoresPendientesResponse>(
    `/rutas-trabajo/${rutaId}/iniciadores-pendientes`,
    { params }
  );
  return data;
};

export const assignRutaItems = async (
  rutaId: number,
  grupoId: number,
  payload: IAssignItemsRequest
): Promise<IAssignItemsResponse> => {
  const { data } = await apiClient.post<IAssignItemsResponse>(
    `/rutas-trabajo/${rutaId}/grupos/${grupoId}/items:assign`,
    payload
  );
  return data;
};

export const moveRutaItem = async (
  rutaId: number,
  itemId: number,
  payload: IMoveItemRequest
): Promise<IMoveItemResponse> => {
  const { data } = await apiClient.patch<IMoveItemResponse>(
    `/rutas-trabajo/${rutaId}/items/${itemId}/move`,
    payload
  );
  return data;
};

export const deleteRutaItem = async (rutaId: number, itemId: number): Promise<IDeleteItemResponse> => {
  const { data } = await apiClient.delete<IDeleteItemResponse>(`/rutas-trabajo/${rutaId}/items/${itemId}`);
  return data;
};

export const deleteRutaGrupo = async (rutaId: number, grupoId: number): Promise<IDeleteGrupoResponse> => {
  const { data } = await apiClient.delete<IDeleteGrupoResponse>(`/rutas-trabajo/${rutaId}/grupos/${grupoId}`);
  return data;
};

export const patchRutaItemOrdenTrabajo = async (
  rutaId: number,
  itemId: number,
  payload: IPatchItemOtRequest
): Promise<IPatchItemOtResponse> => {
  const { data } = await apiClient.patch<IPatchItemOtResponse>(
    `/rutas-trabajo/${rutaId}/items/${itemId}/orden-trabajo`,
    payload
  );
  return data;
};

/** Publica la ruta (BORRADOR → PUBLICADA), crea actuaciones mínimas por ítem. 409 = validación de negocio. */
export const publicarRutaTrabajo = async (rutaId: number): Promise<IPublicarRutaTrabajoResponse> => {
  const { data } = await apiClient.post<IPublicarRutaTrabajoResponse>(
    `/rutas-trabajo/${rutaId}/publicar`
  );
  return data;
};
