import type { IActuacionesPendientesItem } from "../../api/actuacionesPendientesApi";

function esInspeccion(row: IActuacionesPendientesItem): boolean {
  return String(row.tipo_actuacion ?? "").toUpperCase() === "INSPECCION";
}

/** Prefiere actuación INSPECCION origen; ante empate, mayor id (más reciente). */
function preferCanonicalNotificacionRow(
  a: IActuacionesPendientesItem,
  b: IActuacionesPendientesItem
): IActuacionesPendientesItem {
  const aInsp = esInspeccion(a);
  const bInsp = esInspeccion(b);
  if (aInsp && !bInsp) return a;
  if (bInsp && !aInsp) return b;
  return a.id >= b.id ? a : b;
}

/**
 * Una fila por `notificacion_id` en historial (evita duplicar INSPECCION + REINSPECCION).
 */
export function dedupeNotificacionHistorialRows(
  items: IActuacionesPendientesItem[]
): IActuacionesPendientesItem[] {
  const sinNoti: IActuacionesPendientesItem[] = [];
  const byNoti = new Map<number, IActuacionesPendientesItem>();

  for (const row of items) {
    const nid = row.notificacion_id;
    if (nid == null || Number(nid) <= 0) {
      sinNoti.push(row);
      continue;
    }
    const key = Number(nid);
    const prev = byNoti.get(key);
    byNoti.set(key, prev ? preferCanonicalNotificacionRow(prev, row) : row);
  }

  return [...sinNoti, ...byNoti.values()].sort((a, b) => b.id - a.id);
}

/** Clave estable MRT para historial de notificación. */
export function notificacionHistorialRowKey(row: IActuacionesPendientesItem): string {
  if (row.notificacion_id != null && Number(row.notificacion_id) > 0) {
    return `noti-${row.notificacion_id}`;
  }
  return `act-${row.id}`;
}
