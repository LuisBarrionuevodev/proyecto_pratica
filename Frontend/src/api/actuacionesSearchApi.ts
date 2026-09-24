import { apiClient } from "./apiClient";

export interface IActuacionSearchItem {
  id: number;
  label: string;
  orden_trabajo_numero: string | null;
  fecha_actuacion: string | null;
  tipo_actuacion: string | null;
  domicilio_texto: string | null;
  rubro_nombre: string | null;
  contribuyente_texto: string | null;
}

export interface IOrdenSearchItem {
  id: number;
  numero_acta: string;
  anio: number | null;
  label: string;
  tiene_actuacion: boolean;
}

export interface IActuacionesSearchResponse {
  items: IActuacionSearchItem[];
}

export interface IOrdenesSearchResponse {
  items: IOrdenSearchItem[];
}

/**
 * Búsqueda global liviana de actuaciones (debounce + cancelación en el caller).
 */
export async function searchActuaciones(
  q: string,
  limit = 20,
  signal?: AbortSignal
): Promise<IActuacionSearchItem[]> {
  const { data } = await apiClient.get<IActuacionesSearchResponse>("/actuaciones/search", {
    params: { q, limit },
    signal,
  });
  return data.items ?? [];
}

/**
 * Búsqueda de órdenes de trabajo por número.
 */
export async function searchOrdenesTrabajo(
  q: string,
  limit = 20,
  signal?: AbortSignal
): Promise<IOrdenSearchItem[]> {
  const { data } = await apiClient.get<IOrdenesSearchResponse>("/actuaciones/ordenes/search", {
    params: { q, limit },
    signal,
  });
  return data.items ?? [];
}
