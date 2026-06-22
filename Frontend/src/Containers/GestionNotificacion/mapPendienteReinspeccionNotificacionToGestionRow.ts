import type { IActuacionesPendientesItem } from "../../api/actuacionesPendientesApi";

/**
 * Adapta filas de `/actuaciones/pendientes-notificacion` al shape de la bandeja documental.
 * Ese endpoint usa `actuacion_to_grid_row` (sin métricas de plazo del presenter de expediente).
 */
export function mapPendienteReinspeccionNotificacionToGestionRow(
  row: IActuacionesPendientesItem
): IActuacionesPendientesItem {
  return {
    ...row,
    source_type: row.source_type === "NOTIFICACION" ? row.source_type : "NOTIFICACION",
    dias_restantes: row.dias_restantes ?? 0,
    plazos_otorgados: row.plazos_otorgados ?? 0,
  };
}
