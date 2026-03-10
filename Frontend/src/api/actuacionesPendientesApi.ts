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
  source_type?: "NOTIFICACION" | "COMPROBACION";
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

export interface ICreateExpedienteRequest {
  expediente_numero: string;
  expediente_anio: number;
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
    expediente_anio: string;
    source_type?: "NOTIFICACION" | "COMPROBACION";
    next_state_hint?: "PENDIENTE_REINSPECCION" | "ESPERANDO_OFICIO";
    reinspeccion_due_date?: string | null;
    plazo_dias?: number | null;
    prorroga_dias?: number | null;
  };
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

export const getActuacionesPendientesExpediente = async (
  desde?: string | null,
  hasta?: string | null,
  sourceType?: "all" | "notificacion" | "comprobacion"
): Promise<IActuacionesPendientesExpedienteResponse> => {
  const params: Record<string, string> = {};
  if (desde) params.desde = desde;
  if (hasta) params.hasta = hasta;
  if (sourceType) params.source_type = sourceType;
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
