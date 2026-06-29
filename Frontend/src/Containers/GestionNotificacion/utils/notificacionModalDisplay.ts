import type { IActuacionesPendientesItem } from "../../../api/actuacionesPendientesApi";

export type NotificacionDetalleModalVariant = "documental" | "soloExpediente";

function actaNotificacionLinea(row: IActuacionesPendientesItem): string {
  const n = (row.acta_notificacion_num ?? "").trim();
  return n ? `Número de acta de notificación N.º ${n}` : "—";
}

/** Título principal del modal (siempre el mismo; la variante no cambia el H1). */
export function notificacionModalTitulo(
  _variant: NotificacionDetalleModalVariant,
  _esReinspeccionNotificacion: boolean
): string {
  return "Notificación detalle";
}

/** Subtítulo: solo número de acta de notificación (fecha/estado van en el bloque de plazos). */
export function notificacionModalSubtitulo(row: IActuacionesPendientesItem): string {
  return actaNotificacionLinea(row);
}
