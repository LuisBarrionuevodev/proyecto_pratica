import type { IActuacionesPendientesItem } from "../../../api/actuacionesPendientesApi";

export type NotificacionDetalleModalVariant = "documental" | "soloExpediente";

function actaNotificacionLinea(row: IActuacionesPendientesItem): string | null {
  const n = (row.acta_notificacion_num ?? "").trim();
  return n ? `Número de acta de notificación N.º ${n}` : null;
}

function fechaLinea(row: IActuacionesPendientesItem): string | null {
  const f = (row.fecha_actuacion ?? "").trim();
  return f ? `Fecha: ${f}` : null;
}

function estadoLinea(row: IActuacionesPendientesItem): string | null {
  if (row.dias_restantes === null || row.dias_restantes === undefined) return null;
  if (row.dias_restantes === 0) return "Estado: vencido o vence hoy";
  return `Estado: ${row.dias_restantes} días restantes`;
}

/** Título principal del modal (siempre el mismo; la variante no cambia el H1). */
export function notificacionModalTitulo(
  _variant: NotificacionDetalleModalVariant,
  _esReinspeccionNotificacion: boolean
): string {
  return "Notificación detalle";
}

/** Subtítulo con acta de notificación, fecha y estado (sin IDs técnicos). */
export function notificacionModalSubtitulo(row: IActuacionesPendientesItem): string {
  const parts = [actaNotificacionLinea(row), fechaLinea(row), estadoLinea(row)].filter(Boolean) as string[];
  return parts.length ? parts.join(" · ") : "—";
}
