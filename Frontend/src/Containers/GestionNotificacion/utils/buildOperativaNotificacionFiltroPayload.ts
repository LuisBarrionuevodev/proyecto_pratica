/** Payload de filtros operativos compartidos entre tabs de notificación (OPER-RUTA.3). */

export type OperativaNotificacionFiltroPayload = {
  desde: string | null;
  hasta: string | null;
  numeroNotificacion: string | null;
};

export function buildOperativaNotificacionFiltroPayload(input: {
  desde: string | null;
  hasta: string | null;
  numeroNotificacion: string;
}): OperativaNotificacionFiltroPayload {
  const desde = input.desde?.trim() || null;
  const hasta = input.hasta?.trim() || null;
  const numeroNotificacion = input.numeroNotificacion.trim() || null;
  return { desde, hasta, numeroNotificacion };
}

export function operativaNotificacionTieneFiltro(payload: OperativaNotificacionFiltroPayload): boolean {
  return Boolean(payload.desde || payload.hasta || payload.numeroNotificacion);
}
