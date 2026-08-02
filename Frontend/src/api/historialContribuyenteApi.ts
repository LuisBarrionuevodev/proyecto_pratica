import { apiClient } from "./apiClient";
import type {
  IHistorialActasPayload,
  IHistorialTramitesPayload,
} from "./establecimientosOperativosApi";

/** Fila de `GET /establecimientos/historial-contribuyente` (solo consulta). */
export interface IHistorialContribuyenteRow {
  id: number;
  fecha: string | null;
  tipo_actuacion: string | null;
  estado?: string | null;
  realizada?: boolean | null;
  domicilio_texto?: string | null;
  rubro_nombre?: string | null;
  orden_trabajo_numero?: string | null;
  inspectores_texto?: string | null;
  contraproducencia?: string | null;
  observaciones?: string | null;
  actas_tramites_texto?: string | null;
  actas?: IHistorialActasPayload | null;
  tramites?: IHistorialTramitesPayload | null;
  actuacion_id?: number | null;
  iniciador_id?: number | null;
  ruta_item_id?: number | null;
  origen?: string | null;
  titular_visible?: boolean | null;
}

export interface IHistorialContribuyenteMeta {
  total: number;
  page: number;
  limit: number;
  documento_normalizado: string;
}

export interface IHistorialContribuyenteResponse {
  rows: IHistorialContribuyenteRow[];
  meta: IHistorialContribuyenteMeta;
}

export interface IHistorialContribuyenteFilters {
  documento: string;
  desde?: string | null;
  hasta?: string | null;
  page?: number;
  limit?: number;
}

/**
 * Historial completo por DNI/CUIT (solo lectura; no alimenta prefill operativo).
 */
export async function getHistorialContribuyente(
  filters: IHistorialContribuyenteFilters
): Promise<IHistorialContribuyenteResponse> {
  const params: Record<string, string> = {
    documento: filters.documento.trim(),
  };
  if (filters.desde?.trim()) params.desde = filters.desde.trim();
  if (filters.hasta?.trim()) params.hasta = filters.hasta.trim();
  if (filters.page != null) params.page = String(filters.page);
  if (filters.limit != null) params.limit = String(filters.limit);

  const { data } = await apiClient.get<IHistorialContribuyenteResponse>(
    "/establecimientos/historial-contribuyente",
    { params }
  );
  return data;
}
