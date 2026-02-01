import { apiClient } from "./apiClient";
import type { IRelevamientoListItem } from "./relevamientosListApi";

export type RelevamientosPendientesTipo = "domicilios";

export interface IRelevamientosPendientesSummary {
  total: number;
  domicilios: number;
}

export interface IRelevamientosPendientesItem extends IRelevamientoListItem {
  domicilio_id?: number | null;
  calle_normalizada?: string | null;
  calle_estado?: string | null;
  calle_score?: number | null;
  calle_sugerida?: string | null;
  calle_mostrar?: string | null;
  calle_catalogo_id?: number | null;
}

export interface IRelevamientosPendientesFilters {
  tipo: RelevamientosPendientesTipo;
  desde?: string | null;
  hasta?: string | null;
}

export const getRelevamientosPendientesSummary = async (
  desde?: string | null,
  hasta?: string | null
): Promise<IRelevamientosPendientesSummary> => {
  const params: Record<string, string> = {};
  if (desde) params.desde = desde;
  if (hasta) params.hasta = hasta;
  const { data } = await apiClient.get<IRelevamientosPendientesSummary>("/relevamientos/pendientes/summary", { params });
  return data;
};

export const getRelevamientosPendientes = async (
  filters: IRelevamientosPendientesFilters
): Promise<IRelevamientosPendientesItem[]> => {
  const params: Record<string, string> = { tipo: filters.tipo };
  if (filters.desde) params.desde = filters.desde;
  if (filters.hasta) params.hasta = filters.hasta;
  const { data } = await apiClient.get<IRelevamientosPendientesItem[]>("/relevamientos/pendientes", { params });
  return data;
};
