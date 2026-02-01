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
  domicilio_id?: number | null;
  calle_normalizada?: string | null;
  calle_estado?: string | null;
  calle_score?: number | null;
  calle_sugerida?: string | null;
  calle_mostrar?: string | null;
  calle_catalogo_id?: number | null;
}

export interface IActuacionesPendientesFilters {
  tipo: ActuacionesPendientesTipo;
  desde?: string | null;
  hasta?: string | null;
}

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
