import { apiClient } from "./apiClient";

export interface IRelevamientoListItem {
  id: number;
  fecha: string | null;
  inspector: string | null;
  calle: string | null;
  calle_raw?: string | null;
  calle_cargada?: string | null;
  numero: string | null;
  numero_esquina?: string | null;
  numero_tipo?: string | null;
  calle_ingresada?: string | null;
  rubro: string | null;
  domicilio_id?: number | null;
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
  iniciador_ruta_id?: number | null;
  iniciador_estado?: string | null;
  editable?: boolean;
  /** Mapea `turno_carga` en backend (MANIANA | TARDE). */
  turno?: string | null;
  esta_abierto?: boolean | null;
}

export interface IRelevamientosListMeta {
  total: number;
  page: number;
  page_size: number;
  desde: string | null;
  hasta: string | null;
  inspector: string | null;
  calle: string | null;
  numero: string | null;
}

export interface IRelevamientosListResponse {
  items: IRelevamientoListItem[];
  meta: IRelevamientosListMeta;
}

export interface IRelevamientosListFilters {
  desde?: string | null;
  hasta?: string | null;
  inspector?: string | null;
  calle?: string | null;
  numero?: string | null;
  page?: number;
  page_size?: number;
}

/** Listado completo sin filtro de actuación completada (p. ej. otros consumidores de API). */
export const getRelevamientosFiltered = async (
  filters?: IRelevamientosListFilters
): Promise<IRelevamientosListResponse> => {
  const params: Record<string, string> = {};
  if (filters?.desde) params.desde = filters.desde;
  if (filters?.hasta) params.hasta = filters.hasta;
  if (filters?.inspector) params.inspector = filters.inspector;
  if (filters?.calle) params.calle = filters.calle;
  if (filters?.numero) params.numero = filters.numero;
  if (filters?.page) params.page = String(filters.page);
  if (filters?.page_size) params.page_size = String(filters.page_size);

  const { data } = await apiClient.get<IRelevamientosListResponse>("/relevamientos", { params });
  return data;
};

/**
 * Bandeja "Realizados": relevamientos con iniciador RELEVAMIENTO en CUMPLIDO y actuación vinculada
 * (cierre exitoso vía Completar trabajo).
 */
export const getRelevamientosRealizadosActuacionCompletadaFiltered = async (
  filters?: IRelevamientosListFilters
): Promise<IRelevamientosListResponse> => {
  const params: Record<string, string> = {};
  if (filters?.desde) params.desde = filters.desde;
  if (filters?.hasta) params.hasta = filters.hasta;
  if (filters?.inspector) params.inspector = filters.inspector;
  if (filters?.calle) params.calle = filters.calle;
  if (filters?.numero) params.numero = filters.numero;
  if (filters?.page) params.page = String(filters.page);
  if (filters?.page_size) params.page_size = String(filters.page_size);

  const { data } = await apiClient.get<IRelevamientosListResponse>("/relevamientos/realizados", {
    params,
  });
  return data;
};

export const getRelevamientosOperativosFiltered = async (
  filters?: IRelevamientosListFilters
): Promise<IRelevamientosListResponse> => {
  const params: Record<string, string> = {};
  if (filters?.desde) params.desde = filters.desde;
  if (filters?.hasta) params.hasta = filters.hasta;
  if (filters?.inspector) params.inspector = filters.inspector;
  if (filters?.calle) params.calle = filters.calle;
  if (filters?.numero) params.numero = filters.numero;
  if (filters?.page) params.page = String(filters.page);
  if (filters?.page_size) params.page_size = String(filters.page_size);

  const { data } = await apiClient.get<IRelevamientosListResponse>("/relevamientos/gestion-operativa", {
    params,
  });
  return data;
};
