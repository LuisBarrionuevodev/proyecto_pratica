import { apiClient } from "../../../../api/apiClient";
import type { IRutaIniciadorPendienteRow } from "../../../../api/rutasTrabajoApi";
import type {
  IPlanificacionMetricas,
  ICargaDistritoRow,
  PlanificacionOrdenM4,
  UrgentesFiltrosAplicados,
} from "../types/planificacion.types";

export interface IPlanificacionListMeta {
  total: number;
  page: number;
  per_page: number;
}

export async function getPlanificacionMetricas(
  rutaId: number,
  distritoId?: number | null
): Promise<IPlanificacionMetricas> {
  const { data } = await apiClient.get<IPlanificacionMetricas>(
    `/rutas-trabajo/${rutaId}/planificacion/metricas`,
    { params: distritoId != null ? { distrito_id: distritoId } : {} }
  );
  return data;
}

export async function getPlanificacionCargaDistritos(
  rutaId: number
): Promise<{ items: ICargaDistritoRow[] }> {
  const { data } = await apiClient.get<{ items: ICargaDistritoRow[] }>(
    `/rutas-trabajo/${rutaId}/planificacion/carga-distritos`
  );
  return data;
}

export async function getPlanificacionUrgentes(
  rutaId: number,
  params: {
    page?: number;
    per_page?: number;
    distrito_id?: number;
    tipo_urgente?: UrgentesFiltrosAplicados["tipo_urgente"];
    q?: string;
    numero_oficio?: string;
    numero_comprobacion?: string;
  }
): Promise<{ items: IRutaIniciadorPendienteRow[]; meta: IPlanificacionListMeta }> {
  const query: Record<string, string | number> = {};
  if (params.page) query.page = params.page;
  if (params.per_page) query.per_page = params.per_page;
  if (params.distrito_id != null) query.distrito_id = params.distrito_id;
  if (params.tipo_urgente) query.tipo_urgente = params.tipo_urgente;
  if (params.q) query.q = params.q;
  if (params.numero_oficio) query.numero_oficio = params.numero_oficio;
  if (params.numero_comprobacion) query.numero_comprobacion = params.numero_comprobacion;
  const { data } = await apiClient.get<{
    items: IRutaIniciadorPendienteRow[];
    meta: IPlanificacionListMeta;
  }>(`/rutas-trabajo/${rutaId}/planificacion/urgentes`, { params: query });
  return data;
}

export interface IPendientesContextoParams {
  distrito_id: number;
  tipo?: string;
  prioridad_categoria?: "BAJA" | "MEDIA" | "ALTA";
  prioridad?: number;
  q?: string;
  turno_sugerido?: "MANIANA" | "TARDE";
  calle_catalogo_id?: number;
  page?: number;
  per_page?: number;
  orden?: PlanificacionOrdenM4;
}

export async function getPlanificacionPendientesContexto(
  rutaId: number,
  params: IPendientesContextoParams
): Promise<{ items: IRutaIniciadorPendienteRow[]; meta: IPlanificacionListMeta }> {
  const { data } = await apiClient.get<{
    items: IRutaIniciadorPendienteRow[];
    meta: IPlanificacionListMeta;
  }>(`/rutas-trabajo/${rutaId}/planificacion/pendientes-contexto`, { params });
  return data;
}
