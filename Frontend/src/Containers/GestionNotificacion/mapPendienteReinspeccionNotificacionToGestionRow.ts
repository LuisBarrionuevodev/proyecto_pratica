import type { IActuacionesPendientesItem } from "../../api/actuacionesPendientesApi";

/**
 * Adapta filas de `/actuaciones/pendientes-notificacion` al shape de la bandeja documental.
 * El endpoint ya incluye métricas de plazo vía `actuacion_to_pendiente_expediente_row`.
 */
export function mapPendienteReinspeccionNotificacionToGestionRow(
  row: IActuacionesPendientesItem
): IActuacionesPendientesItem {
  return {
    ...row,
    source_type: row.source_type === "NOTIFICACION" ? row.source_type : "NOTIFICACION",
  };
}
