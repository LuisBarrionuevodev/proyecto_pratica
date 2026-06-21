import type { IActuacionesPendientesItem } from "../../api/actuacionesPendientesApi";

/**
 * Clave estable para filas de la cola operativa `/actuaciones/pendientes-notificacion`.
 */
export function reinspeccionNotificacionBandejaRowKey(row: IActuacionesPendientesItem): string {
  const explicit = row.bandeja_row_key?.trim();
  if (explicit) return explicit;
  const ini = row.iniciador_id;
  if (ini != null && Number(ini) > 0) return String(ini);
  return String(row.id);
}
