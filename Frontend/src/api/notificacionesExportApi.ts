import {
  getActuacionesPendientesExpediente,
  getPendientesReinspeccionNotificacion,
  type IActuacionesPendientesItem,
} from "./actuacionesPendientesApi";
import { normalizeNotificacionBandejaItems } from "../Containers/GestionNotificacion/normalizeNotificacionBandejaItems";
import {
  matchesPlazoSlice,
  type PlazoOperativoSlice,
} from "../Containers/GestionNotificacion/gestionNotificacionPlazo";

export type NotificacionesExportFilters = {
  desde: string;
  hasta: string;
  plazoSlice: PlazoOperativoSlice;
  distritoId?: number | null;
  contribuyenteQ?: string | null;
  calleQ?: string | null;
  numeroNotificacion?: string | null;
  motivoQ?: string | null;
};

/**
 * Obtiene todas las notificaciones del rango vía `GET /actuaciones/pendientes/expediente`
 * (sin paginación server). Aplica slice operativo y filtros documentales de historial.
 */
export async function fetchAllNotificacionesForExport(
  filters: NotificacionesExportFilters
): Promise<IActuacionesPendientesItem[]> {
  if (filters.plazoSlice === "vencidas_o_hoy") {
    const rein = await getPendientesReinspeccionNotificacion();
    return normalizeNotificacionBandejaItems(rein, "notificacion");
  }

  const docOpts = {
    contribuyenteQ: filters.contribuyenteQ?.trim() || undefined,
    calleQ: filters.calleQ?.trim() || undefined,
    numeroNotificacion: filters.numeroNotificacion?.trim() || undefined,
    motivoQ: filters.motivoQ?.trim() || undefined,
    plazoSlice:
      filters.plazoSlice === "en_plazo" || filters.plazoSlice === "por_vencer"
        ? filters.plazoSlice
        : undefined,
  };

  const resp = await getActuacionesPendientesExpediente(
    filters.desde,
    filters.hasta,
    "notificacion",
    filters.distritoId ?? null,
    docOpts
  );

  let items = normalizeNotificacionBandejaItems(resp.items, resp.meta.source_type);
  items = items.filter(
    (r) => r.source_type === "NOTIFICACION" || Boolean(String(r.acta_notificacion_num ?? "").trim())
  );

  if (filters.plazoSlice !== "total" && docOpts.plazoSlice == null) {
    items = items.filter((r) => matchesPlazoSlice(r, filters.plazoSlice));
  }

  return items;
}
