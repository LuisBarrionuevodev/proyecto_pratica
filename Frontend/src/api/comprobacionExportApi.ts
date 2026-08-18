import { getActuacionesPendientesExpediente } from "./actuacionesPendientesApi";
import {
  fetchComprobacionPendientesOficio,
  fetchComprobacionRecorrido,
  fetchPendientesReinspeccionOficio,
  type IComprobacionRecorridoListParams,
} from "./actuacionesComprobacionActasApi";
import type { ComprobacionExportRow, ComprobacionExportSlice } from "../Containers/ActasComprobacion/utils/comprobacionExportTypes";
import {
  mapExpedientePendienteRow,
  mapOficioPendienteRow,
  mapRecorridoRow,
  mapReinspeccionPendienteRow,
} from "../Containers/ActasComprobacion/utils/comprobacionesExportMappers";

export type ComprobacionesExportFilters = {
  desde: string;
  hasta: string;
  slice: ComprobacionExportSlice;
  /**
   * Params completos de Recorrido (mismo contrato que el listado).
   * Cuando está presente con slice=recorrido, tiene prioridad sobre desde/hasta sueltos.
   */
  recorridoApiParams?: IComprobacionRecorridoListParams;
  distritoId?: number | null;
  contribuyenteQ?: string | null;
  calleQ?: string | null;
  actaComprobacion?: string | null;
  oficioNumero?: string | null;
  expedienteNumero?: string | null;
  tipoFinal?: string | null;
};

/**
 * Obtiene todas las comprobaciones del rango según el slice activo.
 * Endpoints sin paginación server: una llamada por slice.
 */
export async function fetchAllComprobacionesForExport(
  filters: ComprobacionesExportFilters
): Promise<ComprobacionExportRow[]> {
  const { desde, hasta, slice, distritoId } = filters;

  if (slice === "expediente") {
    const resp = await getActuacionesPendientesExpediente(desde, hasta, "comprobacion", distritoId ?? null);
    return resp.items
      .filter((r) => r.source_type === "COMPROBACION" || Boolean(String(r.acta_comprobacion_num ?? "").trim()))
      .map(mapExpedientePendienteRow);
  }

  if (slice === "oficio") {
    const resp = await fetchComprobacionPendientesOficio(desde, hasta, distritoId ?? null);
    return resp.items.map(mapOficioPendienteRow);
  }

  if (slice === "reinspeccion") {
    const resp = await fetchPendientesReinspeccionOficio(desde, hasta, distritoId ?? null);
    return resp.items.map(mapReinspeccionPendienteRow);
  }

  const resp = await fetchComprobacionRecorrido(
    filters.recorridoApiParams ?? {
      desde,
      hasta,
      distrito_id: distritoId ?? undefined,
      contrib_q: filters.contribuyenteQ?.trim() || undefined,
      calle_q: filters.calleQ?.trim() || undefined,
      acta_comprobacion: filters.actaComprobacion?.trim() || undefined,
      oficio_numero: filters.oficioNumero?.trim() || undefined,
      expediente_numero: filters.expedienteNumero?.trim() || undefined,
      tipo_final: filters.tipoFinal?.trim() || undefined,
    }
  );
  return resp.items.map(mapRecorridoRow);
}
