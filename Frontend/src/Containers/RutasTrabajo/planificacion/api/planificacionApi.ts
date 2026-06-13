import { apiClient } from "../../../../api/apiClient";
import type { IRutaIniciadorPendienteRow } from "../../../../api/rutasTrabajoApi";
import type {
  IPlanificacionMetricas,
  ICargaDistritoRow,
  PlanificacionOrdenM4,
  UrgentesFiltrosAplicados,
} from "../types/planificacion.types";
import { buildUrgentesQueryParams } from "../utils/buildUrgentesQueryParams";

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
    /** Solo para filtros explícitos; no enviar por distrito del mapa. */
    distrito_id?: number | null;
    filtros?: UrgentesFiltrosAplicados;
  }
): Promise<{ items: IRutaIniciadorPendienteRow[]; meta: IPlanificacionListMeta }> {
  const query = buildUrgentesQueryParams(params);
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
  /** STAB-10b: minimal para carga de pins en mapa. */
  fields?: "full" | "minimal";
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
